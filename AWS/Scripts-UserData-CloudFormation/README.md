# Scripts de UserData (CloudFormation)

Scripts bash usados como **UserData** dentro dos templates CloudFormation localizados em `AWS/Templates/`. Eles são executados automaticamente na inicialização da instância EC2, e cuidam da configuração do servidor (instalação de pacotes, montagem de NFS, deploy de WordPress, etc.).

| Arquivo | Descrição |
|---|---|
| `nfsClient.sh` | Configura uma instância como cliente NFS |
| `nfsServer.sh` / `nfsServer1.sh` / `nfs_Server.sh` | Versões do script de configuração do servidor NFS |
| `wordpress.sh` / `wp.sh` / `wp_up.sh` | Versões do script de instalação/deploy do WordPress |
| `wp_bd.sh` / `wpbd_up.sh` | Versões do script de configuração do banco de dados do WordPress |

> Várias versões do mesmo script (ex: `wp.sh`, `wp_up.sh`) representam iterações feitas durante os exercícios práticos.
