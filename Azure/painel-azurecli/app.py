#!/usr/bin/env python3
"""
Backend Flask para o Painel Web de Gerenciamento Azure.

Organizado por serviço:
  /api/vm/...   -> equivalente ao painel EC2 da AWS, usando az vm
  /api/db/...   -> Azure Database for MySQL/PostgreSQL Flexible Server, equivalente ao RDS

DIFERENÇA IMPORTANTE EM RELAÇÃO À AWS:
Praticamente todo recurso na Azure pertence a um RESOURCE GROUP. Por
isso, a maioria das rotas aqui pede o nome do Resource Group além
do nome do recurso (VM, servidor de banco, NSG), diferente da AWS
onde o Instance ID já é suficiente para identificar o recurso.

ATENÇÃO DE SEGURANÇA:
Este servidor executa comandos reais na sua conta Azure (start/stop/
delete de VMs, start/stop de bancos de dados). Foi feito para rodar
LOCALMENTE, para fins de estudo. NÃO exponha esta aplicação na
internet sem autenticação, HTTPS e validação de entrada mais rígida.

Pré-requisito: Azure CLI instalada e autenticada (`az login`)
na máquina onde este script for executado.
"""

import subprocess
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def run_az_command(args):
    """
    Executa um comando da Azure CLI e retorna stdout/stderr/código de saída.
    'args' é uma lista de argumentos (sem o 'az' inicial), por exemplo:
    ['vm', 'list', '--query', '...']
    """
    comando_completo = ["az"] + args
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
        return {"ok": False, "stdout": "", "stderr": "Azure CLI não encontrada. Instale e faça login com 'az login'."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Comando excedeu o tempo limite (45s)."}


def validar_nome(valor):
    """
    Validação simples para evitar injeção de comando via parâmetros de URL.
    Nomes de recursos Azure aceitam letras, números, hífen, underscore e ponto.
    """
    if not valor:
        return False
    return all(c.isalnum() or c in "-_." for c in valor)


@app.route("/")
def index():
    return render_template("index.html")


# =================================================================
# VM (Virtual Machine) - equivalente ao EC2 da AWS
# =================================================================

@app.route("/api/vm/listar/todas")
def vm_listar_todas():
    """Lista todas as VMs com nome, resource group, status de energia e tamanho."""
    resultado = run_az_command([
        "vm", "list",
        "--show-details",
        "--query", "[].{Nome:name, ResourceGroup:resourceGroup, Status:powerState, Tamanho:hardwareProfile.vmSize}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/vm/listar/ips-publicos")
def vm_listar_ips_publicos():
    """Lista nome e IP público de cada VM."""
    resultado = run_az_command([
        "vm", "list-ip-addresses",
        "--query", "[].{Nome:virtualMachine.name, IPPublico:virtualMachine.network.publicIpAddresses[0].ipAddress}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/vm/listar/tamanhos-disponiveis")
def vm_listar_tamanhos_disponiveis():
    """
    Lista os tamanhos de VM (equivalente ao instance type da AWS)
    disponíveis em uma região. Requer o parâmetro de querystring
    'location' (ex: ?location=eastus).
    """
    location = request.args.get("location", "eastus")
    if not validar_nome(location):
        return jsonify({"ok": False, "stderr": "Location inválida."}), 400
    resultado = run_az_command([
        "vm", "list-sizes",
        "--location", location,
        "--query", "[?starts_with(name, 'Standard_B')].{Nome:name, vCPUs:numberOfCores, MemoriaMB:memoryInMb}",
        "--output", "json",
    ])
    return jsonify(resultado)


# Cada distro/imagem tem publisher e offer próprios no Marketplace Azure.
# Igual ao painel AWS, isso evita varrer o catálogo inteiro (--all),
# que demora muito e pode estourar o timeout.
IMAGENS_SUPORTADAS = {
    "ubuntu": {"publisher": "Canonical", "offer": "0001-com-ubuntu-server-jammy"},
    "almalinux": {"publisher": "almalinux", "offer": "almalinux"},
    "rhel": {"publisher": "RedHat", "offer": "RHEL"},
    "debian": {"publisher": "Debian", "offer": "debian-12"},
}


@app.route("/api/vm/listar/imagens/<distro>")
def vm_listar_imagens_por_distro(distro):
    """
    Busca imagens (equivalente à AMI da AWS) de uma distro específica
    (ubuntu, almalinux, rhel ou debian), usando o publisher e offer
    oficiais de cada uma.
    """
    distro = distro.lower()
    if distro not in IMAGENS_SUPORTADAS:
        opcoes = ", ".join(IMAGENS_SUPORTADAS.keys())
        return jsonify({"ok": False, "stderr": f"Distro não suportada. Use uma de: {opcoes}."}), 400

    config = IMAGENS_SUPORTADAS[distro]
    resultado = run_az_command([
        "vm", "image", "list",
        "--publisher", config["publisher"],
        "--offer", config["offer"],
        "--all",
        "--query", "[-20:].{URN:urn, SKU:sku, Versao:version}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/vm/<resource_group>/<vm_name>/detalhes")
def vm_detalhes(resource_group, vm_name):
    """
    Retorna detalhes completos de uma VM específica: status, tamanho,
    IPs, zona, sistema operacional e grupo de recursos.
    """
    if not validar_nome(resource_group) or not validar_nome(vm_name):
        return jsonify({"ok": False, "stderr": "Resource Group ou nome de VM inválido."}), 400
    resultado = run_az_command([
        "vm", "show",
        "--resource-group", resource_group,
        "--name", vm_name,
        "--show-details",
        "--query", (
            "{"
            "Nome:name,"
            "Status:powerState,"
            "Tamanho:hardwareProfile.vmSize,"
            "IPPublico:publicIps,"
            "IPPrivado:privateIps,"
            "Zona:zones,"
            "ResourceGroup:resourceGroup,"
            "Localizacao:location,"
            "SistemaOperacional:storageProfile.osDisk.osType"
            "}"
        ),
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/vm/<resource_group>/<vm_name>/iniciar", methods=["POST"])
def vm_iniciar(resource_group, vm_name):
    if not validar_nome(resource_group) or not validar_nome(vm_name):
        return jsonify({"ok": False, "stderr": "Resource Group ou nome de VM inválido."}), 400
    resultado = run_az_command(["vm", "start", "--resource-group", resource_group, "--name", vm_name])
    return jsonify(resultado)


@app.route("/api/vm/<resource_group>/<vm_name>/parar", methods=["POST"])
def vm_parar(resource_group, vm_name):
    """
    Usa 'az vm deallocate' em vez de 'az vm stop': deallocate libera os
    recursos de computação (e para de cobrar por eles), enquanto stop
    apenas desliga o sistema operacional mas continua cobrando a VM.
    """
    if not validar_nome(resource_group) or not validar_nome(vm_name):
        return jsonify({"ok": False, "stderr": "Resource Group ou nome de VM inválido."}), 400
    resultado = run_az_command(["vm", "deallocate", "--resource-group", resource_group, "--name", vm_name])
    return jsonify(resultado)


@app.route("/api/vm/<resource_group>/<vm_name>/terminar", methods=["POST"])
def vm_terminar(resource_group, vm_name):
    """Remove a VM definitivamente. Os discos e NIC associados podem continuar existindo dependendo da configuração."""
    if not validar_nome(resource_group) or not validar_nome(vm_name):
        return jsonify({"ok": False, "stderr": "Resource Group ou nome de VM inválido."}), 400
    resultado = run_az_command(["vm", "delete", "--resource-group", resource_group, "--name", vm_name, "--yes"])
    return jsonify(resultado)


# ---------------------------------------------------------------
# Network Security Group (NSG) - equivalente ao Security Group da AWS
# ---------------------------------------------------------------

@app.route("/api/nsg/listar/<resource_group>")
def nsg_listar(resource_group):
    """Lista os NSGs de um Resource Group, com suas regras."""
    if not validar_nome(resource_group):
        return jsonify({"ok": False, "stderr": "Resource Group inválido."}), 400
    resultado = run_az_command([
        "network", "nsg", "list",
        "--resource-group", resource_group,
        "--query", "[].{Nome:name, Regras:securityRules[*].{Nome:name, Porta:destinationPortRange, Protocolo:protocol, Acesso:access}}",
        "--output", "json",
    ])
    return jsonify(resultado)


def validar_porta(valor):
    """Valida que a porta informada é um número inteiro dentro da faixa válida (0-65535), ou '*' para todas."""
    if valor == "*":
        return True
    try:
        porta = int(valor)
        return 0 <= porta <= 65535
    except (TypeError, ValueError):
        return False


@app.route("/api/nsg/<resource_group>/<nsg_name>/regra", methods=["POST"])
def nsg_criar_regra(resource_group, nsg_name):
    """
    Cria uma regra de entrada em um NSG existente.
    Espera JSON: {"nome_regra": "AllowSSH", "prioridade": 1000, "porta": 22, "protocolo": "Tcp", "origem": "*"}
    """
    if not validar_nome(resource_group) or not validar_nome(nsg_name):
        return jsonify({"ok": False, "stderr": "Resource Group ou nome de NSG inválido."}), 400

    dados = request.get_json(silent=True) or {}
    nome_regra = dados.get("nome_regra", "")
    prioridade = dados.get("prioridade")
    porta = dados.get("porta")
    protocolo = dados.get("protocolo", "")
    origem = dados.get("origem", "*")

    if not validar_nome(nome_regra):
        return jsonify({"ok": False, "stderr": "Nome da regra inválido."}), 400
    try:
        prioridade = int(prioridade)
        if not (100 <= prioridade <= 4096):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"ok": False, "stderr": "Prioridade inválida. Use um número entre 100 e 4096."}), 400
    if not validar_porta(porta):
        return jsonify({"ok": False, "stderr": "Porta inválida. Use um número entre 0 e 65535, ou '*'."}), 400
    if protocolo not in ("Tcp", "Udp", "*"):
        return jsonify({"ok": False, "stderr": "Protocolo inválido. Use Tcp, Udp ou *."}), 400
    if origem != "*" and not validar_nome(origem.replace("/", "")):
        return jsonify({"ok": False, "stderr": "Origem inválida."}), 400

    resultado = run_az_command([
        "network", "nsg", "rule", "create",
        "--resource-group", resource_group,
        "--nsg-name", nsg_name,
        "--name", nome_regra,
        "--priority", str(prioridade),
        "--destination-port-ranges", str(porta),
        "--protocol", protocolo,
        "--source-address-prefixes", origem,
        "--access", "Allow",
        "--direction", "Inbound",
    ])
    return jsonify(resultado)


# ---------------------------------------------------------------
# Resource Groups e SSH Keys (apoio aos formulários)
# ---------------------------------------------------------------

@app.route("/api/resource-groups/listar")
def resource_groups_listar():
    """Lista os Resource Groups disponíveis na subscription, para popular os formulários."""
    resultado = run_az_command([
        "group", "list",
        "--query", "[].{Nome:name, Localizacao:location}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/ssh-keys/listar")
def ssh_keys_listar():
    """Lista as SSH Public Keys cadastradas como recurso Azure, equivalente aos Key Pairs da AWS."""
    resultado = run_az_command([
        "sshkey", "list",
        "--query", "[].{Nome:name, ResourceGroup:resourceGroup}",
        "--output", "json",
    ])
    return jsonify(resultado)


TAMANHOS_PERMITIDOS = {
    "Standard_B1s", "Standard_B1ms", "Standard_B2s",
}


@app.route("/api/vm/criar", methods=["POST"])
def vm_criar():
    """
    Cria uma nova VM.
    Espera JSON: {"resource_group": "meu-rg", "nome": "minha-vm", "imagem": "Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest", "tamanho": "Standard_B1s", "admin_user": "azureuser", "ssh_key_path": "~/.ssh/id_rsa.pub"}

    Por segurança, o tamanho da VM é restrito a uma lista de tipos
    pequenos/baratos (série B, burstable), evitando criação acidental
    de VMs caras através do formulário.
    """
    dados = request.get_json(silent=True) or {}
    resource_group = dados.get("resource_group", "")
    nome = dados.get("nome", "")
    imagem = dados.get("imagem", "")
    tamanho = dados.get("tamanho", "")
    admin_user = dados.get("admin_user", "")
    ssh_key_path = dados.get("ssh_key_path", "")

    if not validar_nome(resource_group):
        return jsonify({"ok": False, "stderr": "Resource Group inválido."}), 400
    if not validar_nome(nome):
        return jsonify({"ok": False, "stderr": "Nome da VM inválido."}), 400
    if not imagem or ":" not in imagem:
        return jsonify({"ok": False, "stderr": "Imagem inválida. Use o formato publisher:offer:sku:version."}), 400
    if tamanho not in TAMANHOS_PERMITIDOS:
        return jsonify({"ok": False, "stderr": f"Tamanho não permitido neste painel. Use um dos: {', '.join(sorted(TAMANHOS_PERMITIDOS))}."}), 400
    if not validar_nome(admin_user):
        return jsonify({"ok": False, "stderr": "Nome de usuário administrador inválido."}), 400

    args = [
        "vm", "create",
        "--resource-group", resource_group,
        "--name", nome,
        "--image", imagem,
        "--size", tamanho,
        "--admin-username", admin_user,
    ]
    if ssh_key_path:
        args += ["--ssh-key-values", ssh_key_path]
    else:
        args += ["--generate-ssh-keys"]
    args += ["--query", "{ID:id, IPPublico:publicIpAddress}", "--output", "json"]

    resultado = run_az_command(args)
    return jsonify(resultado)


# =================================================================
# Banco de Dados (MySQL/PostgreSQL Flexible Server) - equivalente ao RDS
# =================================================================

@app.route("/api/db/listar/mysql/<resource_group>")
def db_listar_mysql(resource_group):
    """Lista os servidores MySQL Flexible Server de um Resource Group."""
    if not validar_nome(resource_group):
        return jsonify({"ok": False, "stderr": "Resource Group inválido."}), 400
    resultado = run_az_command([
        "mysql", "flexible-server", "list",
        "--resource-group", resource_group,
        "--query", "[].{Nome:name, Versao:version, Status:state, Endpoint:fullyQualifiedDomainName}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/db/listar/postgres/<resource_group>")
def db_listar_postgres(resource_group):
    """Lista os servidores PostgreSQL Flexible Server de um Resource Group."""
    if not validar_nome(resource_group):
        return jsonify({"ok": False, "stderr": "Resource Group inválido."}), 400
    resultado = run_az_command([
        "postgres", "flexible-server", "list",
        "--resource-group", resource_group,
        "--query", "[].{Nome:name, Versao:version, Status:state, Endpoint:fullyQualifiedDomainName}",
        "--output", "json",
    ])
    return jsonify(resultado)


@app.route("/api/db/<engine>/<resource_group>/<server_name>/iniciar", methods=["POST"])
def db_iniciar(engine, resource_group, server_name):
    if engine not in ("mysql", "postgres"):
        return jsonify({"ok": False, "stderr": "Engine inválida. Use mysql ou postgres."}), 400
    if not validar_nome(resource_group) or not validar_nome(server_name):
        return jsonify({"ok": False, "stderr": "Resource Group ou nome de servidor inválido."}), 400
    resultado = run_az_command([engine, "flexible-server", "start", "--resource-group", resource_group, "--name", server_name])
    return jsonify(resultado)


@app.route("/api/db/<engine>/<resource_group>/<server_name>/parar", methods=["POST"])
def db_parar(engine, resource_group, server_name):
    if engine not in ("mysql", "postgres"):
        return jsonify({"ok": False, "stderr": "Engine inválida. Use mysql ou postgres."}), 400
    if not validar_nome(resource_group) or not validar_nome(server_name):
        return jsonify({"ok": False, "stderr": "Resource Group ou nome de servidor inválido."}), 400
    resultado = run_az_command([engine, "flexible-server", "stop", "--resource-group", resource_group, "--name", server_name])
    return jsonify(resultado)


if __name__ == "__main__":
    # debug=True facilita o desenvolvimento, mas nunca deve ser usado em produção
    app.run(host="127.0.0.1", port=5001, debug=True)
