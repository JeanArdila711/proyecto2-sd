"""Prueba desechable del Punto 8: ¿API Gateway (HTTP API, HTTP_PROXY) puede ponerse delante de Streamlit?

  python punto8-visualizacion-app/prueba_apigw_streamlit.py crear    # EC2 t3.small con Streamlit de prueba + HTTP API proxy
  python punto8-visualizacion-app/prueba_apigw_streamlit.py probar   # directo vs. API Gateway: /, /_stcore/health y handshake WebSocket
  python punto8-visualizacion-app/prueba_apigw_streamlit.py borrar   # API, EC2 y security group

Se corre desde la raíz del repo (usa comun/config.py para la sesión). Todo lleva Project=proyecto2-sd y
Name=NOMBRE; cada subcomando encuentra lo del anterior por nombre, sin archivos de estado.
"""
import base64
import http.client
import os
import sys

sys.path.insert(0, os.getcwd())
from comun import config  # noqa: E402

NOMBRE = "tlc-prueba-streamlit"
PUERTO = 8501
AMI_PARAM = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
TAGS = [{"Key": "Project", "Value": config.PROYECTO}, {"Key": "Name", "Value": NOMBRE}]
USER_DATA = f"""#!/bin/bash
set -eux
dnf install -y python3.11
python3.11 -m venv /opt/st
/opt/st/bin/pip install -q streamlit
cat > /opt/app.py <<'EOF'
import streamlit as st
st.title("Prueba API Gateway -> Streamlit")
st.write("Si ves esto con el botón funcionando, el WebSocket está conectado.")
st.button("click")
EOF
/opt/st/bin/streamlit --version > /opt/version.txt
nohup /opt/st/bin/streamlit run /opt/app.py --server.port {PUERTO} --server.address 0.0.0.0 \\
  --server.headless true --server.enableCORS false --server.enableXsrfProtection false > /opt/st.log 2>&1 &
"""

aws = config.sesion(config.cargar())
ec2, apigw, ssm = aws.client("ec2"), aws.client("apigatewayv2"), aws.client("ssm")


def instancia():
    r = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [NOMBRE]},
                                        {"Name": "instance-state-name", "Values": ["pending", "running"]}])
    insts = [i for res in r["Reservations"] for i in res["Instances"]]
    return insts[0] if insts else None


def api():
    return next((a for a in apigw.get_apis()["Items"] if a["Name"] == NOMBRE), None)


def sg_id():
    sgs = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [NOMBRE]}])["SecurityGroups"]
    return sgs[0]["GroupId"] if sgs else None


def crear():
    vpc = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    sg = sg_id()
    if not sg:
        sg = ec2.create_security_group(GroupName=NOMBRE, Description="prueba Punto 8, se borra al terminar",
                                       VpcId=vpc, TagSpecifications=[{"ResourceType": "security-group",
                                                                      "Tags": TAGS}])["GroupId"]
        # Abierto a internet solo durante la prueba: API Gateway llama al endpoint público desde IPs de AWS
        ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[{
            "IpProtocol": "tcp", "FromPort": PUERTO, "ToPort": PUERTO, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
    i = instancia()
    if not i:
        ami = ssm.get_parameter(Name=AMI_PARAM)["Parameter"]["Value"]
        i = ec2.run_instances(ImageId=ami, InstanceType="t3.small", MinCount=1, MaxCount=1,
                              SecurityGroupIds=[sg], UserData=USER_DATA,
                              IamInstanceProfile={"Name": "LabInstanceProfile"},
                              TagSpecifications=[{"ResourceType": "instance", "Tags": TAGS}])["Instances"][0]
    ec2.get_waiter("instance_running").wait(InstanceIds=[i["InstanceId"]])
    ip = instancia()["PublicIpAddress"]
    print(f"EC2 {i['InstanceId']} en {ip}")
    if not api():
        a = apigw.create_api(Name=NOMBRE, ProtocolType="HTTP", Tags={"Project": config.PROYECTO})
        for ruta, uri in (("ANY /", f"http://{ip}:{PUERTO}/"),
                          ("ANY /{proxy+}", f"http://{ip}:{PUERTO}/{{proxy}}")):
            integ = apigw.create_integration(ApiId=a["ApiId"], IntegrationType="HTTP_PROXY",
                                             IntegrationMethod="ANY", IntegrationUri=uri,
                                             PayloadFormatVersion="1.0")
            apigw.create_route(ApiId=a["ApiId"], RouteKey=ruta, Target=f"integrations/{integ['IntegrationId']}")
        apigw.create_stage(ApiId=a["ApiId"], StageName="$default", AutoDeploy=True)
    print(f"API {api()['ApiEndpoint']}")
    print("Streamlit tarda ~2-3 min en instalarse; después: probar")


def pedir(conn_cls, host, puerto, ruta, ws=False):
    """(status, primeras cabeceras/cuerpo). Con ws=True manda el handshake de WebSocket (RFC 6455)."""
    c = conn_cls(host, puerto, timeout=15)
    cab = {"Host": host}
    if ws:
        cab.update({"Connection": "Upgrade", "Upgrade": "websocket", "Sec-WebSocket-Version": "13",
                    "Sec-WebSocket-Key": base64.b64encode(os.urandom(16)).decode()})
    try:
        c.request("GET", ruta, headers=cab)
        r = c.getresponse()
        extra = r.getheader("Upgrade") if ws else r.read(80).decode(errors="replace").replace("\n", " ")
        return r.status, extra
    except Exception as e:  # noqa: BLE001  (prueba: cualquier falla de red es un resultado)
        return "error", repr(e)[:120]
    finally:
        c.close()


def probar():
    ip, endpoint = instancia()["PublicIpAddress"], api()["ApiEndpoint"].removeprefix("https://")
    destinos = {"directo": (http.client.HTTPConnection, ip, PUERTO),
                "api_gateway": (http.client.HTTPSConnection, endpoint, 443)}
    for nombre, (cls, host, puerto) in destinos.items():
        print(f"== {nombre}")
        for ruta, ws in (("/", False), ("/_stcore/health", False), ("/_stcore/stream", True)):
            estado, extra = pedir(cls, host, puerto, ruta, ws)
            print(f"  {'WS ' if ws else 'GET'} {ruta:<18} -> {estado}  {extra}")
    print(f"Navegador: https://{endpoint}/   y   http://{ip}:{PUERTO}/")


def borrar():
    if a := api():
        apigw.delete_api(ApiId=a["ApiId"])
        print("API borrada")
    if i := instancia():
        ec2.terminate_instances(InstanceIds=[i["InstanceId"]])
        ec2.get_waiter("instance_terminated").wait(InstanceIds=[i["InstanceId"]])
        print("EC2 terminada")
    if sg := sg_id():
        ec2.delete_security_group(GroupId=sg)
        print("SG borrado")


{"crear": crear, "probar": probar, "borrar": borrar}[sys.argv[1]]()
