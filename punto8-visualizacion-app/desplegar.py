#!/usr/bin/env python3
"""Despliega el Punto 8: API Gateway → Lambda con los resultados de P1–P6, y Streamlit en una EC2 que la consume.

  Navegador ──http:8501──> Streamlit (EC2 tlc-streamlit, t3.small)
                               │ GET /resultados/{pregunta}
                               ▼
                  API Gateway (HTTP API tlc-resultados) ──> Lambda tlc-resultados ──> s3://<bucket>/resultados/

Streamlit va adelante de API Gateway y no detrás: API Gateway no deja pasar el WebSocket de Streamlit
(prueba_apigw_streamlit.py y README.md). Idempotente: reutiliza lo que ya existe y actualiza el código.

  python punto8-visualizacion-app/desplegar.py                  # crea o actualiza todo e imprime las URL
  python punto8-visualizacion-app/desplegar.py --ip 1.2.3.4     # abre el 8501 a otra IP (además de la actual)
  python punto8-visualizacion-app/desplegar.py --apagar         # detiene la EC2 (la API y la Lambda no cobran en reposo)
  python punto8-visualizacion-app/desplegar.py --borrar         # borra la EC2, el security group, la API y la Lambda
"""
import argparse
import io
import sys
import time
import zipfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(DIR.parent), str(DIR.parent / "punto2-fuentes" / "infra")]

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

import crear_infra as infra  # noqa: E402  (Punto 2: vpc_por_defecto, asegurar_sg, permitir, ip_publica, AMI_PARAM)

APP = DIR / "app"
ARCHIVOS_APP = ["app.py", "analisis.py", "test_app.py", "requirements.txt", ".streamlit/config.toml"]
PREFIJO_APP = R["s3_prefijo_codigo"] + "punto8-visualizacion-app/app/"
PUERTO = 8501
DIR_EC2 = "/opt/tlc-app"


def log(msg):
    print(f"[punto8] {msg}", flush=True)


def user_data(bucket):
    """Instala Python 3.11 y Streamlit (findings.md: el python3 de AL2023 es 3.9) y deja un servicio systemd.
    actualizar.sh baja la app de S3 y reinicia el servicio; desplegar.py lo vuelve a correr por SSM."""
    return f"""#!/bin/bash
set -euxo pipefail
dnf install -y python3.11 awscli-2
mkdir -p {DIR_EC2}
cat > {DIR_EC2}/actualizar.sh <<'EOF'
#!/bin/bash
set -euo pipefail
aws s3 cp --recursive --only-show-errors s3://{bucket}/{PREFIJO_APP} {DIR_EC2}/app/
[ -x {DIR_EC2}/venv/bin/python ] || python3.11 -m venv {DIR_EC2}/venv
{DIR_EC2}/venv/bin/pip install --quiet -r {DIR_EC2}/app/requirements.txt
systemctl restart tlc-streamlit
EOF
chmod +x {DIR_EC2}/actualizar.sh
cat > /etc/systemd/system/tlc-streamlit.service <<'EOF'
[Unit]
Description=Streamlit del Punto 8 (proyecto2-sd)
Wants=network-online.target
After=network-online.target
[Service]
WorkingDirectory={DIR_EC2}/app
ExecStart={DIR_EC2}/venv/bin/streamlit run app.py
Restart=always
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable tlc-streamlit
{DIR_EC2}/actualizar.sh
"""


# ------------------------------------------------------------------ Lambda + API
def zip_lambda():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(DIR / "lambda_resultados.py", "lambda_resultados.py")
    return buf.getvalue()


def asegurar_lambda(lam, rol, bucket):
    nombre = R["lambda_resultados"]
    ajustes = dict(Role=rol, Handler="lambda_resultados.handler", Runtime="python3.12", Timeout=15,
                   MemorySize=512, Description="proyecto2-sd Punto 8: resultados de P1-P6 para API Gateway",
                   Environment={"Variables": {"BUCKET": bucket,
                                              "PREFIJO": R["resultados_prefijo"] + "punto6/athena/"}})
    try:
        lam.get_function(FunctionName=nombre)
        lam.update_function_code(FunctionName=nombre, ZipFile=zip_lambda())
        lam.get_waiter("function_updated_v2").wait(FunctionName=nombre)
        lam.update_function_configuration(FunctionName=nombre, **ajustes)
        lam.get_waiter("function_updated_v2").wait(FunctionName=nombre)
        log(f"Lambda {nombre}: actualizada")
    except lam.exceptions.ResourceNotFoundException:
        lam.create_function(FunctionName=nombre, Code={"ZipFile": zip_lambda()},
                            Tags={"Project": config.PROYECTO}, **ajustes)
        lam.get_waiter("function_active_v2").wait(FunctionName=nombre)
        log(f"Lambda {nombre}: creada")
    return lam.get_function(FunctionName=nombre)["Configuration"]["FunctionArn"]


def buscar_api(apigw):
    return next((x for x in apigw.get_apis()["Items"] if x["Name"] == R["api_resultados"]), None)


def asegurar_api(apigw, lam, arn_lambda, region, cuenta):
    api = buscar_api(apigw)
    if api:
        log(f"API {R['api_resultados']}: ya existe")
    else:
        api = apigw.create_api(Name=R["api_resultados"], ProtocolType="HTTP", Tags={"Project": config.PROYECTO},
                               CorsConfiguration={"AllowOrigins": ["*"], "AllowMethods": ["GET"]})
        integ = apigw.create_integration(ApiId=api["ApiId"], IntegrationType="AWS_PROXY",
                                         IntegrationUri=arn_lambda, PayloadFormatVersion="2.0")
        for ruta in ("GET /resultados", "GET /resultados/{pregunta}"):
            apigw.create_route(ApiId=api["ApiId"], RouteKey=ruta, Target=f"integrations/{integ['IntegrationId']}")
        apigw.create_stage(ApiId=api["ApiId"], StageName="$default", AutoDeploy=True)
        log(f"API {R['api_resultados']}: creada")
    # API Gateway necesita permiso para invocar la Lambda. Se reemplaza siempre: si la API se recreó con otro
    # ApiId, un permiso viejo apuntaría a la API anterior y todas las rutas darían 500.
    try:
        lam.remove_permission(FunctionName=R["lambda_resultados"], StatementId="apigw-resultados")
    except lam.exceptions.ResourceNotFoundException:
        pass
    lam.add_permission(FunctionName=R["lambda_resultados"], StatementId="apigw-resultados",
                       Action="lambda:InvokeFunction", Principal="apigateway.amazonaws.com",
                       SourceArn=f"arn:aws:execute-api:{region}:{cuenta}:{api['ApiId']}/*/*/resultados*")
    return api["ApiEndpoint"]


# ------------------------------------------------------------------ EC2 con Streamlit
def publicar_app(s3, bucket, url_api):
    for nombre in ARCHIVOS_APP:
        s3.upload_file(str(APP / nombre), bucket, PREFIJO_APP + nombre)
    s3.put_object(Bucket=bucket, Key=PREFIJO_APP + "api_url.txt", Body=url_api.encode())
    log(f"app publicada en s3://<bucket>/{PREFIJO_APP}")


def buscar_ec2(ec2, estados=("pending", "running", "stopping", "stopped")):
    r = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [R["ec2_streamlit"]]},
                                        {"Name": "tag:Project", "Values": [config.PROYECTO]},
                                        {"Name": "instance-state-name", "Values": list(estados)}])
    inst = [i for res in r["Reservations"] for i in res["Instances"]]
    return inst[0] if inst else None


def asegurar_ec2(ec2, ssm, sg, bucket):
    inst = buscar_ec2(ec2)
    if inst:
        if inst["State"]["Name"] in ("stopping", "stopped"):
            ec2.get_waiter("instance_stopped").wait(InstanceIds=[inst["InstanceId"]])
            ec2.start_instances(InstanceIds=[inst["InstanceId"]])
            log(f"EC2 {R['ec2_streamlit']}: arrancando")
        ec2.get_waiter("instance_running").wait(InstanceIds=[inst["InstanceId"]])
        return inst["InstanceId"], False
    ami = ssm.get_parameter(Name=infra.AMI_PARAM)["Parameter"]["Value"]
    inst = ec2.run_instances(
        ImageId=ami, InstanceType="t3.small", MinCount=1, MaxCount=1, SecurityGroupIds=[sg],
        IamInstanceProfile={"Name": R["ec2_perfil"]}, UserData=user_data(bucket),
        MetadataOptions={"HttpTokens": "required"},
        TagSpecifications=[{"ResourceType": "instance", "Tags": config.etiquetas(R["ec2_streamlit"])},
                           {"ResourceType": "volume", "Tags": config.etiquetas(R["ec2_streamlit"])}])["Instances"][0]
    log(f"EC2 {R['ec2_streamlit']}: creada ({inst['InstanceId']}); instala Python y Streamlit en ~3 min")
    ec2.get_waiter("instance_running").wait(InstanceIds=[inst["InstanceId"]])
    return inst["InstanceId"], True


def en_ec2(ssm, instancia, comando):
    """Corre un comando en la EC2 por SSM (findings.md: Session Manager funciona con LabInstanceProfile) y
    devuelve su salida; falla con el error del comando si no sale bien."""
    for _ in range(20):  # el agente de SSM tarda en registrarse después de arrancar
        info = ssm.describe_instance_information(Filters=[{"Key": "InstanceIds", "Values": [instancia]}])
        if info["InstanceInformationList"]:
            break
        time.sleep(15)
    else:
        raise SystemExit(f"La EC2 {instancia} no apareció en SSM en 5 min: revisar que tenga LabInstanceProfile.")
    cmd = ssm.send_command(InstanceIds=[instancia], DocumentName="AWS-RunShellScript", TimeoutSeconds=60,
                           Parameters={"commands": [comando], "executionTimeout": ["900"]})["Command"]["CommandId"]
    while True:  # termina: SSM corta el comando a los 900 s (executionTimeout) y lo marca TimedOut
        time.sleep(5)
        try:
            r = ssm.get_command_invocation(CommandId=cmd, InstanceId=instancia)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        if r["Status"] not in ("Pending", "InProgress", "Delayed"):
            break
    if r["Status"] != "Success":
        raise SystemExit(f"Falló en la EC2 ({comando}):\n{r['StandardOutputContent'][-1500:]}"
                         f"\n{r['StandardErrorContent'][-1500:]}")
    return r["StandardOutputContent"].strip()


def abrir_puerto(ec2, sg, ips):
    """Deja el 8501 abierto exactamente a `ips`: agrega las nuevas y quita las de corridas anteriores
    (otra red, otra sala), para que el puerto no quede abierto a IPs que ya no presentan."""
    regla = {"IpProtocol": "tcp", "FromPort": PUERTO, "ToPort": PUERTO}
    actuales = {r["CidrIp"] for p in ec2.describe_security_groups(GroupIds=[sg])["SecurityGroups"][0]["IpPermissions"]
                if p.get("FromPort") == PUERTO for r in p.get("IpRanges", [])}
    if viejas := actuales - set(ips):
        ec2.revoke_security_group_ingress(GroupId=sg, IpPermissions=[
            {**regla, "IpRanges": [{"CidrIp": ip} for ip in sorted(viejas)]}])
        log(f"puerto {PUERTO} cerrado a {', '.join(sorted(viejas))}")
    for ip in ips:
        infra.permitir(ec2, sg, {**regla, "IpRanges": [{"CidrIp": ip, "Description": "presentador"}]})
    log(f"puerto {PUERTO} abierto a {', '.join(ips)}")


# ------------------------------------------------------------------ apagar / borrar
def apagar(ec2):
    inst = buscar_ec2(ec2, ("pending", "running"))
    if inst:
        ec2.stop_instances(InstanceIds=[inst["InstanceId"]])
        log(f"EC2 {R['ec2_streamlit']}: deteniéndose")
    else:
        log(f"EC2 {R['ec2_streamlit']}: no está encendida")


def borrar(ec2, apigw, lam):
    if api := buscar_api(apigw):
        apigw.delete_api(ApiId=api["ApiId"])
        log("API borrada")
    try:
        lam.delete_function(FunctionName=R["lambda_resultados"])
        log("Lambda borrada")
    except lam.exceptions.ResourceNotFoundException:
        pass
    if inst := buscar_ec2(ec2):
        ec2.terminate_instances(InstanceIds=[inst["InstanceId"]])
        ec2.get_waiter("instance_terminated").wait(InstanceIds=[inst["InstanceId"]])
        log("EC2 terminada")
    sgs = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [R["sg_streamlit"]]}])
    for sg in sgs["SecurityGroups"]:
        for intento in range(12):  # la interfaz de red de la EC2 tarda en soltarse después de terminarla
            try:
                ec2.delete_security_group(GroupId=sg["GroupId"])
                log("security group borrado")
                break
            except ec2.exceptions.ClientError as e:
                if e.response["Error"]["Code"] != "DependencyViolation" or intento == 11:
                    raise
                time.sleep(10)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ip", action="append", default=[], help="otra IP que puede abrir la app (se puede repetir)")
    p.add_argument("--apagar", action="store_true")
    p.add_argument("--borrar", action="store_true")
    args = p.parse_args()
    aws = config.sesion(config.cargar())
    ec2, ssm, s3 = aws.client("ec2"), aws.client("ssm"), aws.client("s3")
    lam, apigw = aws.client("lambda"), aws.client("apigatewayv2")
    if args.apagar:
        return apagar(ec2)
    if args.borrar:
        return borrar(ec2, apigw, lam)

    bucket = config.nombre_bucket(aws)
    cuenta = aws.client("sts").get_caller_identity()["Account"]
    arn = asegurar_lambda(lam, f"arn:aws:iam::{cuenta}:role/LabRole", bucket)
    url_api = asegurar_api(apigw, lam, arn, aws.region_name, cuenta)
    publicar_app(s3, bucket, url_api)

    sg = infra.asegurar_sg(ec2, infra.vpc_por_defecto(ec2), R["sg_streamlit"],
                           "Streamlit del Punto 8: puerto 8501 solo desde las IP de quien presenta")
    abrir_puerto(ec2, sg, [infra.ip_publica()] + [f"{x}/32" if "/" not in x else x for x in args.ip])
    instancia, nueva = asegurar_ec2(ec2, ssm, sg, bucket)
    if nueva:  # la app la instala el user data; se espera a que termine para poder probarla
        en_ec2(ssm, instancia, "cloud-init status --wait")
    else:
        en_ec2(ssm, instancia, f"{DIR_EC2}/actualizar.sh")
    log("EC2: app instalada y servicio reiniciado")
    log("prueba: " + en_ec2(ssm, instancia, f"cd {DIR_EC2}/app && ../venv/bin/python test_app.py 2>&1 | tail -3"))
    ip_ec2 = ec2.describe_instances(InstanceIds=[instancia])["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    print(f"\nAPI:       {url_api}/resultados")
    print(f"Streamlit: http://{ip_ec2}:{PUERTO}/" + ("   (listo en ~3 min)" if nueva else ""))


if __name__ == "__main__":
    main()
