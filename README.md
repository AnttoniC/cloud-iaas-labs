# cloud-iaas-labs

Práticas de Computação em Nuvem com o modelo de serviço **IaaS** (Infrastructure as a Service), cobrindo os dois principais provedores trabalhados ao longo dos estudos: **AWS** e **Azure**.

Este repositório reúne templates de infraestrutura como código (CloudFormation e ARM Templates), scripts de automação (bash) e painéis web próprios para a AWS CLI e a Azure CLI, desenvolvidos como parte de exercícios práticos da disciplina de Cloud Computing.

## Estrutura do repositório

```
cloud-iaas-labs/
├── AWS/
│   ├── Templates/                          → Templates CloudFormation (.json), organizados por exercício
│   │   ├── 01-servidor-simples/            → VPC + Security Group + instância EC2
│   │   ├── 02-servidor-web-ssh/            → Servidor com acesso Web + SSH
│   │   ├── 03-wordpress/                   → Instância configurada para rodar WordPress
│   │   ├── 04-vpc-multicamada/             → VPC com subnets, rotas, gateway e múltiplos servidores
│   │   └── 05-cluster-autoscaling/         → Cluster com Auto Scaling, Load Balancer e RDS
│   ├── Scripts/                            → Scripts bash de gerenciamento (menus, deploy, listagem de instâncias)
│   ├── Scripts-UserData-CloudFormation/    → Scripts de UserData usados dentro dos templates CloudFormation (NFS, WordPress)
│   └── painel-awscli/                      → Painel web (Flask) que executa comandos AWS CLI via navegador
│
├── Azure/
│   ├── Templates/                          → ARM Templates (.json), organizados por exercício
│   │   ├── 01-vm-linux/                    → Criação de VMs Linux/Ubuntu
│   │   ├── 02-storage/                     → Conta de armazenamento (Storage Account)
│   │   └── 03-modulos-arm/                 → Templates modulares (ARM linked templates)
│   ├── Scripts/                            → Scripts bash de gerenciamento (criar/listar/deletar VM, ARM, NFS)
│   └── painel-azurecli/                    → Painel web (Flask) que executa comandos Azure CLI via navegador
│
└── README.md
```

## Sobre a organização

Os templates dentro de cada subpasta numerada (`01-`, `02-`, ...) representam a **evolução de um mesmo exercício**: do rascunho inicial até a versão final/funcional. Os nomes de arquivo foram padronizados, mas o conteúdo original de cada versão foi mantido — nada foi descartado, já que o objetivo deste repositório é documentar o processo de aprendizado, não apenas o resultado final.

Arquivos com sufixo `-final` ou o de maior número dentro da pasta tendem a ser a versão mais completa/corrigida daquele exercício.

## Painel Web para AWS CLI (AWS/painel-awscli)

Interface web (Python + Flask) que executa comandos reais da AWS CLI a partir de botões e formulários no navegador, organizada em abas EC2 e RDS. Cobre listagem de instâncias, IPs, AMIs (incluindo busca por distro: Ubuntu, AlmaLinux, Red Hat, Debian), Security Groups, Key Pairs, criação de instância, e iniciar/parar/terminar recursos. Veja `AWS/painel-awscli/README.md` para instruções de uso e a lista completa de funcionalidades.

## Painel Web para Azure CLI (Azure/painel-azurecli)

Réplica da mesma metodologia do painel AWS, adaptada para os conceitos da Azure: organizado em abas Virtual Machines e Banco de Dados (MySQL/PostgreSQL Flexible Server). Cobre listagem de VMs, IPs, tamanhos disponíveis, busca de imagens por distro, detalhes de VM, Network Security Groups, SSH Keys, criação/exclusão de Resource Group, criação de VM, e iniciar/parar/terminar recursos. Veja `Azure/painel-azurecli/README.md` para instruções de uso e a lista completa de funcionalidades.

> Atenção: ambos os painéis executam comandos reais nas contas AWS/Azure configuradas na máquina. Feitos para uso local/estudo — não devem ser expostos na internet sem autenticação.

## Tecnologias

- **AWS**: CloudFormation, EC2, VPC, Security Groups, Auto Scaling, RDS, Elastic Load Balancing
- **Azure**: Azure Resource Manager (ARM Templates), Máquinas Virtuais, Network Security Groups, Resource Groups, Azure Database for MySQL/PostgreSQL
- **Scripts**: Bash (automação via AWS CLI e Azure CLI)
- **Painéis Web**: Python, Flask

## Observação

Repositório com fins de estudo. Os templates aqui presentes não devem ser usados em produção sem revisão de segurança (chaves, IPs liberados, credenciais em texto plano, etc.).
