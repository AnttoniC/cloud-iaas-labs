#!/usr/bin/env python3
"""
Backend Flask para o Menu Web de Gerenciamento AWS.

Organizado por serviço:
  /api/ec2/...  -> equivalente a menuListarDataInstancia.sh e menuIniciarInsta.sh
  /api/rds/...  -> consulta e controle básico de instâncias RDS

ATENÇÃO DE SEGURANÇA:
Este servidor executa comandos reais na sua conta AWS (start/stop/
terminate de instâncias EC2, start/stop de instâncias RDS). Foi feito
para rodar LOCALMENTE, para fins de estudo. NÃO exponha esta aplicação
na internet sem autenticação, HTTPS e validação de entrada mais
rígida - caso contrário, qualquer pessoa que acessar o endereço
poderá controlar seus recursos AWS.

Pré-requisito: AWS CLI instalada e configurada (`aws configure`)
na máquina onde este script for executado.
"""

import subprocess
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def run_aws_command(args):
    """
    Executa um comando da AWS CLI e retorna stdout/stderr/código de saída.
    'args' é uma lista de argumentos (sem o 'aws' inicial), por exemplo:
    ['ec2', 'describe-instances', '--query', '...']
    """
    comando_completo = ["aws"] + args
    try:
        resultado = subprocess.run(
            comando_completo,
            capture_output=True,
            text=True,
            timeout=45,
        )
        return {
            "ok": resultado.returncode == 0,
            "stdout": resultado.stdout.strip(),
            "stderr": resultado.stderr.strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "stderr": "AWS CLI não encontrada. Instale e configure com 'aws configure'."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Comando excedeu o tempo limite (45s)."}


def validar_id(valor, prefixo=None):
    """
    Validação simples para evitar injeção de comando via parâmetros de URL.
    Aceita apenas caracteres alfanuméricos e hífen, opcionalmente
    exigindo um prefixo (ex: 'i-' para instâncias EC2).
    """
    if not valor:
        return False
    if prefixo and not valor.startswith(prefixo):
        return False
    return all(c.isalnum() or c == "-" for c in valor)


@app.route("/")
def index():
    return render_template("index.html")


# =================================================================
# EC2 - equivalente a menuListarDataInstancia.sh e menuIniciarInsta.sh
# =================================================================

@app.route("/api/ec2/listar/ips-publicos")
def ec2_listar_ips_publicos():
    resultado = run_aws_command([
        "ec2", "describe-instances",
        "--query", "Reservations[].Instances[].PublicIpAddress",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/listar/image-ids")
def ec2_listar_image_ids():
    resultado = run_aws_command([
        "ec2", "describe-instances",
        "--filters", "Name=tag:Name,Values=*",
        "--query", "Reservations[].Instances[].ImageId",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/listar/ips-privados")
def ec2_listar_ips_privados():
    resultado = run_aws_command([
        "ec2", "describe-instances",
        "--filters", "Name=tag:Name,Values=*",
        "--query", "Reservations[].Instances[].PrivateIpAddress",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/listar/nomes")
def ec2_listar_nomes():
    resultado = run_aws_command([
        "ec2", "describe-instances",
        "--filters", "Name=tag:Name,Values=*",
        "--query", "Reservations[].Instances[].Tags",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/listar/amis-linux")
def ec2_listar_amis_linux():
    """
    Lista as AMIs Linux da PRÓPRIA conta (--owners self).
    Limitado de propósito a 'self' para responder rápido: buscar nas
    AMIs públicas da Amazon sem um filtro de nome específico retorna
    milhares de imagens e costuma estourar o timeout da requisição.
    """
    resultado = run_aws_command([
        "ec2", "describe-images",
        "--owners", "self",
        "--filters", "Name=platform-details,Values=Linux/UNIX",
        "--query", "Images[*].{ID:ImageId,Nome:Name,Descricao:Description}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/listar/amis-amazon-linux-recente")
def ec2_listar_amis_amazon_linux_recente():
    """
    Lista as AMIs Linux mais recentes publicadas pela Amazon
    (Amazon Linux 2023 e Amazon Linux 2), usando um filtro de nome
    específico para evitar buscar no catálogo público inteiro.
    """
    resultado = run_aws_command([
        "ec2", "describe-images",
        "--owners", "amazon",
        "--filters",
        "Name=name,Values=al2023-ami-*,amzn2-ami-hvm-*",
        "Name=architecture,Values=x86_64",
        "Name=state,Values=available",
        "--query", "Images[*].{ID:ImageId,Nome:Name,Descricao:Description}",
        "--output", "json",
    ])
    return jsonify(resultado)


# Cada distro tem um "owner" (conta AWS que publica as AMIs oficiais)
# e um padrão de nome diferente. Usar esses dois filtros junto evita
# varrer o catálogo público inteiro - sem isso, a busca demora muito
# e pode estourar o timeout da requisição.
DISTROS_SUPORTADAS = {
    "ubuntu": {
        "owner": "099720109477",  # Canonical
        "padrao_nome": "ubuntu/images/hvm-ssd*/ubuntu-*-*-amd64-server-*",
    },
    "almalinux": {
        "owner": "764336703387",  # AlmaLinux OS Foundation
        "padrao_nome": "AlmaLinux OS *",
    },
    "rhel": {
        "owner": "309956199498",  # Red Hat
        "padrao_nome": "RHEL-*",
    },
    "debian": {
        "owner": "136693071363",  # Debian
        "padrao_nome": "debian-*",
    },
}


@app.route("/api/ec2/listar/amis-por-distro/<distro>")
def ec2_listar_amis_por_distro(distro):
    """
    Busca AMIs de uma distro Linux específica (ubuntu, almalinux, rhel
    ou debian), usando o owner e o padrão de nome oficial de cada uma.
    Retorna as 20 imagens mais recentes, ordenadas da mais nova para a
    mais antiga, para manter a resposta rápida e relevante.
    """
    distro = distro.lower()
    if distro not in DISTROS_SUPORTADAS:
        opcoes = ", ".join(DISTROS_SUPORTADAS.keys())
        return jsonify({"ok": False, "stderr": f"Distro não suportada. Use uma de: {opcoes}."}), 400

    config = DISTROS_SUPORTADAS[distro]
    resultado = run_aws_command([
        "ec2", "describe-images",
        "--owners", config["owner"],
        "--filters",
        f"Name=name,Values={config['padrao_nome']}",
        "Name=architecture,Values=x86_64",
        "Name=state,Values=available",
        "--query", "reverse(sort_by(Images, &CreationDate))[:20].{ID:ImageId,Nome:Name,Descricao:Description,Criacao:CreationDate}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/listar/subredes")
def ec2_listar_subredes():
    resultado = run_aws_command([
        "ec2", "describe-subnets",
        "--filters", "Name=cidr,Values=*",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/listar/ids-e-nomes")
def ec2_listar_ids_e_nomes():
    resultado = run_aws_command([
        "ec2", "describe-instances",
        "--filters", "Name=tag:Name,Values=*",
        "--query", "Reservations[].Instances[*].{ID:InstanceId,tag:Tags}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/instancia/<instance_id>/detalhes")
def ec2_detalhes_instancia(instance_id):
    """
    Retorna detalhes completos de uma instância específica: status,
    tipo, AMI usada, data de lançamento, IPs, security groups e zona
    de disponibilidade.
    """
    if not validar_id(instance_id, prefixo="i-"):
        return jsonify({"ok": False, "stderr": "Instance ID inválido."}), 400
    resultado = run_aws_command([
        "ec2", "describe-instances",
        "--instance-ids", instance_id,
        "--query", (
            "Reservations[0].Instances[0].{"
            "InstanceId:InstanceId,"
            "Status:State.Name,"
            "Tipo:InstanceType,"
            "AMI:ImageId,"
            "Lancamento:LaunchTime,"
            "IPPublico:PublicIpAddress,"
            "IPPrivado:PrivateIpAddress,"
            "ZonaDisponibilidade:Placement.AvailabilityZone,"
            "VPC:VpcId,"
            "Subnet:SubnetId,"
            "SecurityGroups:SecurityGroups[*].GroupName,"
            "KeyName:KeyName"
            "}"
        ),
        "--output", "json",
    ])
    return jsonify(resultado)


# ---------------------------------------------------------------
# Security Groups
# ---------------------------------------------------------------

@app.route("/api/ec2/security-groups/listar")
def ec2_listar_security_groups():
    """Lista todos os Security Groups com suas regras de entrada/saída."""
    resultado = run_aws_command([
        "ec2", "describe-security-groups",
        "--query", (
            "SecurityGroups[*].{"
            "ID:GroupId,"
            "Nome:GroupName,"
            "Descricao:Description,"
            "VPC:VpcId,"
            "RegrasEntrada:IpPermissions[*].{Porta:FromPort,Protocolo:IpProtocol,Origem:IpRanges[0].CidrIp}"
            "}"
        ),
        "--output", "json",
    ])
    return jsonify(resultado)


def validar_porta(valor):
    """Valida que a porta informada é um número inteiro dentro da faixa válida (0-65535)."""
    try:
        porta = int(valor)
        return 0 <= porta <= 65535
    except (TypeError, ValueError):
        return False


def validar_cidr(valor):
    """
    Validação simples de bloco CIDR (ex: 0.0.0.0/0, 192.168.1.0/24).
    Não é uma validação completa de IP, mas bloqueia o suficiente
    para evitar injeção de comando via este campo.
    """
    if not valor or "/" not in valor:
        return False
    ip_parte, _, prefixo = valor.partition("/")
    octetos = ip_parte.split(".")
    if len(octetos) != 4:
        return False
    if not all(o.isdigit() and 0 <= int(o) <= 255 for o in octetos):
        return False
    return prefixo.isdigit() and 0 <= int(prefixo) <= 32


@app.route("/api/ec2/security-groups/<group_id>/regra", methods=["POST"])
def ec2_criar_regra_security_group(group_id):
    """
    Cria uma regra de entrada (ingress) em um Security Group existente.
    Espera JSON: {"protocolo": "tcp", "porta": 22, "cidr": "0.0.0.0/0"}
    """
    if not validar_id(group_id, prefixo="sg-"):
        return jsonify({"ok": False, "stderr": "Security Group ID inválido."}), 400

    dados = request.get_json(silent=True) or {}
    protocolo = dados.get("protocolo", "")
    porta = dados.get("porta")
    cidr = dados.get("cidr", "")

    if protocolo not in ("tcp", "udp", "icmp"):
        return jsonify({"ok": False, "stderr": "Protocolo inválido. Use tcp, udp ou icmp."}), 400
    if not validar_porta(porta):
        return jsonify({"ok": False, "stderr": "Porta inválida. Use um número entre 0 e 65535."}), 400
    if not validar_cidr(cidr):
        return jsonify({"ok": False, "stderr": "CIDR inválido. Use o formato 0.0.0.0/0."}), 400

    resultado = run_aws_command([
        "ec2", "authorize-security-group-ingress",
        "--group-id", group_id,
        "--protocol", protocolo,
        "--port", str(porta),
        "--cidr", cidr,
    ])
    return jsonify(resultado)


# ---------------------------------------------------------------
# Criação de nova instância
# ---------------------------------------------------------------

@app.route("/api/ec2/key-pairs/listar")
def ec2_listar_key_pairs():
    """Lista os Key Pairs disponíveis na conta, para popular o formulário de criação."""
    resultado = run_aws_command([
        "ec2", "describe-key-pairs",
        "--query", "KeyPairs[*].KeyName",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ec2/security-groups/listar-nomes")
def ec2_listar_security_group_nomes():
    """Lista nome e ID dos Security Groups, para popular o formulário de criação."""
    resultado = run_aws_command([
        "ec2", "describe-security-groups",
        "--query", "SecurityGroups[*].{ID:GroupId,Nome:GroupName}",
        "--output", "json",
    ])
    return jsonify(resultado)


TIPOS_INSTANCIA_PERMITIDOS = {
    "t2.micro", "t2.small", "t2.medium",
    "t3.micro", "t3.small", "t3.medium",
}


@app.route("/api/ec2/instancia/criar", methods=["POST"])
def ec2_criar_instancia():
    """
    Cria uma nova instância EC2.
    Espera JSON: {"ami": "ami-xxxx", "tipo": "t2.micro", "key_name": "minha-chave", "security_group": "sg-xxxx" (opcional), "nome": "minha-instancia" (opcional)}

    Por segurança, o tipo de instância é restrito a uma lista de
    tipos pequenos/gratuitos (free tier), evitando criação acidental
    de instâncias caras através do formulário.
    """
    dados = request.get_json(silent=True) or {}
    ami = dados.get("ami", "")
    tipo = dados.get("tipo", "")
    key_name = dados.get("key_name", "")
    security_group = dados.get("security_group", "")
    nome = dados.get("nome", "")

    if not validar_id(ami, prefixo="ami-"):
        return jsonify({"ok": False, "stderr": "AMI ID inválido."}), 400
    if tipo not in TIPOS_INSTANCIA_PERMITIDOS:
        return jsonify({"ok": False, "stderr": f"Tipo de instância não permitido neste painel. Use um dos: {', '.join(sorted(TIPOS_INSTANCIA_PERMITIDOS))}."}), 400
    if not key_name or not all(c.isalnum() or c in "-_" for c in key_name):
        return jsonify({"ok": False, "stderr": "Nome do Key Pair inválido."}), 400
    if security_group and not validar_id(security_group, prefixo="sg-"):
        return jsonify({"ok": False, "stderr": "Security Group ID inválido."}), 400
    if nome and not all(c.isalnum() or c in "-_ " for c in nome):
        return jsonify({"ok": False, "stderr": "Nome da instância contém caracteres inválidos."}), 400

    args = [
        "ec2", "run-instances",
        "--image-id", ami,
        "--instance-type", tipo,
        "--key-name", key_name,
        "--count", "1",
    ]
    if security_group:
        args += ["--security-group-ids", security_group]
    if nome:
        args += ["--tag-specifications", f"ResourceType=instance,Tags=[{{Key=Name,Value={nome}}}]"]
    args += ["--query", "Instances[0].InstanceId", "--output", "text"]

    resultado = run_aws_command(args)
    return jsonify(resultado)


@app.route("/api/ec2/instancia/<instance_id>/iniciar", methods=["POST"])
def ec2_iniciar_instancia(instance_id):
    if not validar_id(instance_id, prefixo="i-"):
        return jsonify({"ok": False, "stderr": "Instance ID inválido."}), 400
    resultado = run_aws_command(["ec2", "start-instances", "--instance-ids", instance_id])
    return jsonify(resultado)


@app.route("/api/ec2/instancia/<instance_id>/parar", methods=["POST"])
def ec2_parar_instancia(instance_id):
    if not validar_id(instance_id, prefixo="i-"):
        return jsonify({"ok": False, "stderr": "Instance ID inválido."}), 400
    resultado = run_aws_command(["ec2", "stop-instances", "--instance-ids", instance_id])
    return jsonify(resultado)


@app.route("/api/ec2/instancia/<instance_id>/terminar", methods=["POST"])
def ec2_terminar_instancia(instance_id):
    if not validar_id(instance_id, prefixo="i-"):
        return jsonify({"ok": False, "stderr": "Instance ID inválido."}), 400
    resultado = run_aws_command(["ec2", "terminate-instances", "--instance-ids", instance_id])
    return jsonify(resultado)


# =================================================================
# RDS - consulta e controle básico de instâncias de banco de dados
# =================================================================

@app.route("/api/rds/listar/instancias")
def rds_listar_instancias():
    """Lista identificador, engine, status e endpoint de cada instância RDS."""
    resultado = run_aws_command([
        "rds", "describe-db-instances",
        "--query", "DBInstances[*].{ID:DBInstanceIdentifier,Engine:Engine,Status:DBInstanceStatus,Endpoint:Endpoint.Address}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/rds/listar/status")
def rds_listar_status():
    """Lista apenas identificador e status (útil pra checar rápido se está disponível)."""
    resultado = run_aws_command([
        "rds", "describe-db-instances",
        "--query", "DBInstances[*].{ID:DBInstanceIdentifier,Status:DBInstanceStatus}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/rds/listar/engines-disponiveis")
def rds_listar_engines():
    """Lista as engines de banco de dados suportadas pela RDS (MySQL, PostgreSQL, etc)."""
    resultado = run_aws_command([
        "rds", "describe-db-engine-versions",
        "--query", "DBEngineVersions[*].Engine",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/rds/instancia/<db_instance_id>/iniciar", methods=["POST"])
def rds_iniciar_instancia(db_instance_id):
    if not validar_id(db_instance_id):
        return jsonify({"ok": False, "stderr": "DB Instance Identifier inválido."}), 400
    resultado = run_aws_command(["rds", "start-db-instance", "--db-instance-identifier", db_instance_id])
    return jsonify(resultado)


@app.route("/api/rds/instancia/<db_instance_id>/parar", methods=["POST"])
def rds_parar_instancia(db_instance_id):
    if not validar_id(db_instance_id):
        return jsonify({"ok": False, "stderr": "DB Instance Identifier inválido."}), 400
    resultado = run_aws_command(["rds", "stop-db-instance", "--db-instance-identifier", db_instance_id])
    return jsonify(resultado)


if __name__ == "__main__":
    # debug=True facilita o desenvolvimento, mas nunca deve ser usado em produção
    app.run(host="127.0.0.1", port=5000, debug=True)
