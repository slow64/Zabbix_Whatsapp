# Zabbix Alerts to WhatsApp

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Zabbix](https://img.shields.io/badge/Zabbix-5.0+-orange.svg)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Web-green.svg)

Este projeto monitora alertas do Zabbix e os envia para um grupo específico no WhatsApp, além de armazená-los em um arquivo Excel para histórico.

## 📋 Tabela de Conteúdos
- [Funcionalidades](#funcionalidades)
- [Pré-requisitos](#pre-requisitos)
- [Como Usar](#como-usar)
<a name="funcionalidades"></a>
## ✨ Funcionalidades

- ✅ Monitoramento contínuo de alertas do Zabbix
- 📲 Envio automatizado para grupo no WhatsApp
- 💾 Armazenamento em Excel com histórico
- 🔍 Filtragem por severidade (ignora alertas de baixa/média prioridade)
- ⚡ Cache de IPs para melhor desempenho
- ✨ Mensagens formatadas com emojis e informações organizadas
<a name="pre-requisitos"></a>
## 📋 Pré-requisitos

Antes de começar, você precisará ter instalado:

- Python 3.8+
- Firefox
- Geckodriver

Instale as dependências Python:
```bash
pip install requests selenium pandas
```
<a name="como-usar"></a>
## 🚀 **Como Usar**
Execute o script:
```bash
python zabbix_alerts.py
```
Escaneie o QR code do WhatsApp Web quando solicitado

O sistema irá:
- Verificar novos alertas a cada 5 segundos
- Enviar mensagens formatadas para o grupo do WhatsApp
- Armazenar o histórico no arquivo alertas.xlsx
