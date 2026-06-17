# Painel Web para AWS CLI

Interface web (Python + Flask) que executa comandos reais da AWS CLI a partir de botões e formulários no navegador, em vez de digitar comandos no terminal. Cobre EC2 e RDS, organizados em abas.

Esta pasta corresponde a `AWS/painel-awscli` dentro do repositório `cloud-iaas-labs`.

## Pré-requisitos

1. **Python 3** instalado
2. **AWS CLI** instalada e configurada com credenciais válidas:
   ```bash
   aws configure
   ```
3. **Flask**:
   ```bash
   pip install flask
   ```

## Como rodar

```bash
cd painel-awscli
python3 app.py
```

Depois, abra no navegador: **http://127.0.0.1:5000**

## Estrutura de arquivos

```
painel-awscli/
├── app.py                 → backend Flask: rotas da API e execução dos comandos AWS CLI
├── templates/
│   └── index.html         → frontend: layout, abas EC2/RDS e lógica de chamada à API
├── README.md
└── .gitignore
```

## O que cada serviço oferece

A interface tem duas abas, EC2 e RDS, cada uma com seu próprio submenu.

### EC2

| Item do menu | O que faz |
|---|---|
| IPs públicos | Lista o IP público de todas as instâncias |
| Image IDs | Lista a AMI usada por cada instância com Tag "Name" |
| IPs privados | Lista o IP privado de todas as instâncias com Tag "Name" |
| Nomes (Tags) | Lista todas as Tags das instâncias |
| Minhas AMIs Linux | Lista as AMIs Linux da própria conta (`--owners self`) |
| Amazon Linux (recentes) | Lista as AMIs Amazon Linux 2023 / Amazon Linux 2 mais recentes publicadas pela AWS |
| Buscar por distro | Dropdown para buscar AMIs recentes de Ubuntu, AlmaLinux, Red Hat (RHEL) ou Debian, usando o owner e padrão de nome oficial de cada fabricante |
| Subredes | Lista subredes com bloco CIDR definido |
| IDs e nomes | Lista o Instance ID junto com as Tags de cada instância |
| Detalhes de uma instância | Status, tipo, AMI, data de lançamento, IPs, zona de disponibilidade, VPC, subnet, security groups e key pair de um Instance ID específico |
| Listar Key Pairs | Lista os nomes dos Key Pairs disponíveis na conta/região configurada — útil para confirmar o nome certo antes de criar uma instância |
| Listar Security Groups | Lista todos os Security Groups com suas regras de entrada |
| Criar regra de entrada | Libera uma porta/protocolo para um bloco CIDR em um Security Group existente |
| Criar nova instância | Formulário com AMI, tipo de instância, Key Pair e Security Group opcional |
| Iniciar / Parar / Terminar | Inicia, para ou termina uma instância pelo Instance ID |

> A criação de instância é restrita a tipos pequenos (t2.micro, t2.small, t2.medium, t3.micro, t3.small, t3.medium) para evitar custo inesperado por engano no formulário.

> As buscas de AMI usam filtros de nome e owner específicos por design: buscar no catálogo público inteiro da AWS sem esses filtros retorna milhares de imagens e costuma estourar o tempo limite da requisição (45s).

### RDS

| Item do menu | O que faz |
|---|---|
| Instâncias (engine, status, endpoint) | Lista todas as instâncias RDS com engine, status atual e endpoint de conexão |
| Status rápido | Lista só identificador e status (útil pra checar disponibilidade rapidamente) |
| Engines disponíveis | Lista as engines de banco suportadas pela RDS na sua conta/região |
| Iniciar / Parar instância | Inicia ou para uma instância pelo DB Instance Identifier |

> RDS não oferece "terminar" por este painel — excluir um banco de dados na AWS exige parâmetros extras (como decidir sobre snapshot final), então essa ação foi deixada de fora por segurança. Use a AWS CLI ou o Console para isso.

## Avisos importantes

- **Isso roda comandos reais na sua conta AWS.** Criar, iniciar, parar ou terminar uma instância EC2, criar regras de Security Group, ou iniciar/parar uma instância RDS pelo painel web tem o mesmo efeito que rodar o comando equivalente na AWS CLI diretamente.
- **Não exponha esse servidor na internet** sem adicionar autenticação (login/senha), HTTPS e um proxy reverso. Da forma como está, qualquer pessoa com acesso ao endereço `http://127.0.0.1:5000` (ou ao IP da máquina, se você abrir a porta) consegue controlar seus recursos AWS.
- `debug=True` no `app.py` é útil durante o desenvolvimento, mas deve ser removido/desativado caso este código seja usado fora de um ambiente local de estudo.
- Os campos de entrada (Instance ID, Security Group ID, CIDR, porta, etc.) passam por validação no backend antes de chegar à AWS CLI, mas isso não substitui boas práticas de segurança caso o projeto evolua para uso real.
