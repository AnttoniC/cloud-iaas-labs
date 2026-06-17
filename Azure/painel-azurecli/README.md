# Painel Web para Azure CLI

Interface web (Python + Flask) que executa comandos reais da Azure CLI a partir de botões e formulários no navegador, em vez de digitar comandos no terminal. Cobre Virtual Machines e Banco de Dados (MySQL/PostgreSQL Flexible Server), organizados em abas.

Esta pasta corresponde a `Azure/painel-azurecli` dentro do repositório `cloud-iaas-labs`, e replica a mesma metodologia usada em `AWS/painel-awscli`.

## Pré-requisitos

1. **Python 3** instalado
2. **Azure CLI** instalada e autenticada:
   ```bash
   az login
   ```
3. **Flask**:
   ```bash
   pip install flask
   ```

## Como rodar

```bash
cd painel-azurecli
python3 app.py
```

Depois, abra no navegador: **http://127.0.0.1:5001**

> Nota: este painel usa a porta **5001** (diferente da porta 5000 do painel AWS), permitindo rodar os dois ao mesmo tempo sem conflito.

## Estrutura de arquivos

```
painel-azurecli/
├── app.py                 → backend Flask: rotas da API e execução dos comandos Azure CLI
├── templates/
│   └── index.html         → frontend: layout, abas VM/Banco de Dados e lógica de chamada à API
├── README.md
└── .gitignore
```

## Diferença importante em relação ao painel AWS

Na AWS, o Instance ID já identifica uma instância de forma única. Na Azure, praticamente todo recurso pertence a um **Resource Group**, então a maioria das ações aqui pede tanto o nome do Resource Group quanto o nome do recurso (VM, NSG, servidor de banco). Use a opção "Listar Resource Groups" para confirmar os nomes disponíveis na sua subscription.

## O que cada serviço oferece

### Virtual Machines (VM)

| Item do menu | O que faz |
|---|---|
| Listar todas | Lista todas as VMs com nome, Resource Group, status de energia e tamanho |
| IPs públicos | Lista nome e IP público de cada VM |
| Tamanhos disponíveis | Lista os tamanhos de VM da série B (burstable) disponíveis em uma região |
| Buscar imagem por distro | Dropdown para buscar imagens recentes de Ubuntu, AlmaLinux, Red Hat (RHEL) ou Debian, retornando a URN (publisher:offer:sku:version) |
| Detalhes de uma VM | Status, tamanho, IPs, zona, sistema operacional e Resource Group de uma VM específica |
| Listar Resource Groups | Lista os Resource Groups disponíveis na subscription |
| Listar SSH Keys | Lista as SSH Public Keys cadastradas como recurso Azure |
| Listar NSGs | Lista os Network Security Groups de um Resource Group, com suas regras |
| Criar regra de entrada | Cria uma regra de entrada (Allow/Inbound) em um NSG existente |
| Criar nova VM | Formulário com Resource Group, nome, imagem (URN), tamanho (restrito à série B), usuário administrador e chave SSH opcional |
| Iniciar / Parar / Terminar | Inicia, desaloca (`az vm deallocate`) ou apaga uma VM |

> A criação de VM é restrita à série B (Standard_B1s, Standard_B1ms, Standard_B2s) para evitar custo inesperado por engano no formulário.

> "Parar" usa `az vm deallocate` em vez de `az vm stop`: deallocate libera os recursos de computação e interrompe a cobrança pela VM, enquanto stop apenas desliga o sistema operacional mas continua cobrando.

> As buscas de imagem usam publisher e offer específicos por design: buscar no catálogo Marketplace inteiro (`--all` sem filtro) demora muito e pode estourar o tempo limite da requisição (45s).

### Banco de Dados

| Item do menu | O que faz |
|---|---|
| Listar servidores MySQL | Lista os servidores MySQL Flexible Server de um Resource Group, com versão, status e endpoint |
| Listar servidores PostgreSQL | Lista os servidores PostgreSQL Flexible Server de um Resource Group |
| Iniciar / Parar servidor | Inicia ou para um servidor MySQL ou PostgreSQL pelo nome e Resource Group |

> Assim como no painel AWS, não há opção de "terminar"/excluir banco de dados por este painel — essa ação fica reservada à Azure CLI ou ao Portal, por segurança.

## Avisos importantes

- **Isso roda comandos reais na sua conta Azure.** Criar, iniciar, parar ou terminar uma VM, criar regras de NSG, ou iniciar/parar um servidor de banco de dados pelo painel web tem o mesmo efeito que rodar o comando equivalente na Azure CLI diretamente.
- **Não exponha esse servidor na internet** sem adicionar autenticação (login/senha), HTTPS e um proxy reverso. Da forma como está, qualquer pessoa com acesso ao endereço `http://127.0.0.1:5001` (ou ao IP da máquina, se você abrir a porta) consegue controlar seus recursos Azure.
- `debug=True` no `app.py` é útil durante o desenvolvimento, mas deve ser removido/desativado caso este código seja usado fora de um ambiente local de estudo.
- Os campos de entrada (nomes de recursos, portas, prioridades, etc.) passam por validação no backend antes de chegar à Azure CLI, mas isso não substitui boas práticas de segurança caso o projeto evolua para uso real.
