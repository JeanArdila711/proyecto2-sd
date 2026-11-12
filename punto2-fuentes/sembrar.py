#!/usr/bin/env python3
"""Siembra las fuentes del Punto 2: esquema de MariaDB, tabla taxi_zones y carpeta de yellow en la EC2.

Corre ec2/sembrar.py dentro de la EC2 por Session Manager (ver remoto.py). Es idempotente.

Uso (desde la raíz del repo, después de infra/crear_infra.py):
  python punto2-fuentes/sembrar.py
"""
from remoto import correr_en_ec2

if __name__ == "__main__":
    correr_en_ec2("sembrar.py", timeout=900)
