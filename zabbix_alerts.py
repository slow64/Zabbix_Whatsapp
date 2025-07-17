import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import pandas as pd

zabbix_url = 'http://seudominio/zabbix/api_jsonrpc.php'

def obter_ip_do_host(auth_token, host_id, ip_cache={}):

    if host_id in ip_cache:
        print(f"IP encontrado no cache para o host_id {host_id}: {ip_cache[host_id]}")
        return ip_cache[host_id]

    zabbix_url = 'http://seudominio/zabbix/api_jsonrpc.php' 
    headers = {'Content-Type': 'application/json-rpc'}

    data_ip = {
        "jsonrpc": "2.0",
        "method": "hostinterface.get",
        "params": {
            "output": "extend",
            "hostids": host_id 
        },
        "auth": auth_token, 
        "id": 1  
    }

    try:
        
        print(f"Enviando requisição para obter IP do host_id {host_id}...")
        response_ip = requests.post(zabbix_url, headers=headers, data=json.dumps(data_ip))

       
        if response_ip.status_code == 200:
            response_data_ip = response_ip.json()
            print("Resposta da API (hostinterface.get):", json.dumps(response_data_ip, indent=4))

            if 'result' in response_data_ip:
                interfaces = response_data_ip['result']

                if interfaces:  
                    ip = interfaces[0].get("ip", "IP não encontrado")
                    print(f"IP encontrado para o host_id {host_id}: {ip}")
                    ip_cache[host_id] = ip  # Armazenar IP no cache
                    return ip

                else:
                    print(f"Nenhuma interface encontrada para o host_id {host_id}.")
                    return "IP não encontrado"

            else:
                print("Erro: Resposta da API não contém o campo 'result'.")
                return "Erro: Resposta da API não contém o campo 'result'."

        else:
            print(f"Erro na requisição: Status code {response_ip.status_code}")
            return f"Erro na requisição: Status code {response_ip.status_code}"
    
    except requests.exceptions.RequestException as e:
        # Captura erros de rede, como falhas na conexão
        print(f"Erro na requisição: {str(e)}")
        return f"Erro na requisição: {str(e)}"

def obter_ultimo_valor_item(auth_token, item_id):
    # Parâmetros para buscar o último valor do item
    headers = {'Content-Type': 'application/json-rpc'}
    data_item = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": ["itemid", "name", "lastvalue", "lastclock"],  # Campos desejados
            "itemids": item_id  # ID do item que você deseja consultar
        },
        "auth": auth_token,
        "id": 1
    }

    try:
        response_item = requests.post(zabbix_url, headers=headers, data=json.dumps(data_item))
        if response_item.status_code == 200:
            response_data_item = response_item.json()
            items = response_data_item.get('result', [])
            if items:  # Se houver itens na lista
                return items[0]  # Retorna o primeiro item (um dicionário)
            else:
                return {}  # Retorna um dicionário vazio se não houver itens
        else:
            print(f"Erro na requisição: Status code {response_item.status_code}")
            return {}
    
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {str(e)}")
        return {}

# Função para obter o nome do host (novo método)
def obter_nome_do_host(auth_token, host_id):
    """Consulta a API do Zabbix para obter o nome do host."""
    zabbix_url = 'http://seudominio/zabbix/api_jsonrpc.php'
    headers = {
        'Content-Type': 'application/json',
    }

    data_nome = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["host"],
            "hostids": host_id
        },
        "auth": auth_token,
        "id": 3
    }

    response_nome = requests.post(zabbix_url, headers=headers, data=json.dumps(data_nome))
    response_data_nome = response_nome.json()

    hosts = response_data_nome.get("result", [])
    if hosts:
        return hosts[0].get("host", "Nome do host não encontrado")
    
    return "Nome do host não encontrado"


# Função para obter os alertas (modificado para usar trigger.get)
def obter_alertas_zabbix(auth_token, last_change_timestamp):
    zabbix_url = 'http://seudominio/zabbix/api_jsonrpc.php'
    
    headers = {
        'Content-Type': 'application/json',
    }

    # Solicitação dos alertas após o timestamp da última mudança (lastchange)
    data_alerts = {
        "jsonrpc": "2.0",
        "method": "trigger.get",  # Usando trigger.get ao invés de problem.get
        "params": {
            "output": ["triggerid", "description", "priority", "lastchange", "value", "hostid", "status"],
            "filter": {"status": 0},  # Filtra apenas triggers ativas
            "sortfield": "lastchange",
            "sortorder": "ASC",  # Ordena os triggers por lastchange em ordem crescente
            "selectHosts": ["hostid", "name"],
            "time_from": int(last_change_timestamp) + 1  # Pega apenas alertas com lastchange maior que o último timestamp
        },
        "auth": auth_token,
        "id": 2
    }

    response_alerts = requests.post(zabbix_url, headers=headers, data=json.dumps(data_alerts))
    response_data = response_alerts.json()

    alerts = response_data.get("result", [])
    
    # Imprimir a severidade de todos os alertas
    for alert in alerts:
        severidade = alert.get('priority', 'N/A')
    
    return alerts


# Função para formatar a mensagem de alerta
def formatar_mensagem_alerta(alert, auth_token, item, ip_cache={}):
    # Verifica se 'alert' é um dicionário
    if not isinstance(alert, dict):
        print("Alerta não é um dicionário:", alert)
        return "Erro: Estrutura do alerta inválida"

    severidade = alert.get('priority', 'N/A')
    if severidade in ["1", "2"]:  # Severidade 1 (Alta) ou 2 (Média)
        print(f"Ignorando alerta de severidade {severidade} (não enviar mensagem).")
        return None  # Retorna None para indicar que o alerta não deve ser enviado

    # Depuração: Exibir a estrutura completa do alerta
    print("Estrutura completa do alerta:", json.dumps(alert, indent=4))

    # Verifica a severidade do alerta
    
    problema = alert.get('description', 'N/A').replace('{HOST.NAME}', '')
    trigger_id = alert.get('triggerid', 'N/A')

    # Extrair o hostid do campo 'hosts'
    hosts = alert.get('hosts', [])
    if hosts:
        host_id = hosts[0].get('hostid', "Host não disponível")
        host_name = hosts[0].get('name', 'Nome do host não encontrado')
    else:
        host_id = "Host não disponível"
        host_name = "Nome do host não encontrado"

    # Depuração: Verificar o host_id
    print(f"Host ID do alerta: {host_id}")

    # Verificar se o host_id é válido
    if host_id == "Host não disponível":
        print("Erro: hostid não está presente no alerta.")
        return "Erro: hostid não está presente no alerta."

    # Extraindo IP do host
    ip_host = obter_ip_do_host(auth_token, host_id, ip_cache)
    print(f"IP do host {host_id}: {ip_host}")

    # Mapeamento de severidade para texto mais legível
    severidade_map = {
        "0": "Desconhecido",
        "1": "Informação",
        "2": "Baixa",
        "3": "Média",
        "4": "Alta",
        "5": "Desastre"
    }
    
    severidade_texto = severidade_map.get(str(severidade), "Desconhecida")

    # Data do evento (última mudança)
    timestamp = alert.get('lastchange', None)
    if timestamp:
        # Convertendo o timestamp para UTC e subtraindo 3 horas
        data_utc = datetime.utcfromtimestamp(int(timestamp))
        data_corrigida = data_utc - timedelta(hours=3) + timedelta(minutes=2)  # Subtrair 3 horas
        data = data_corrigida.strftime('%Y-%m-%d %H:%M:%S')
    else:
        data = "Data não disponível"

    # Determinar se o alerta foi resolvido ou não
    value = alert.get('value', '1')  # Valor padrão é "1" (problema ativo)
    resolved = "*RESOLVIDO* ✅" if value == "0" else "*NÃO RESOLVIDO* ❌"

    # Pegar o último valor do item e formatar para 2 casas decimais
    try:
        ultimo_valor = float(item.get('lastvalue', 0))  # Converte para float
        ultimo_valor_formatado = "{:.2f}".format(ultimo_valor)  # Formata para 2 casas decimais
    except (ValueError, TypeError):
        ultimo_valor_formatado = "N/A"  # Caso o valor não seja um número

    # Formatando a mensagem com o novo escopo
    mensagem = (
        f"{resolved}"
        f"\n*Problema:* {problema}"
        f"\n*Nome:* {host_name}"  # Emoji de lápis
        f"\n*Data:* {data}"  # Emoji de calendário
        f"\n*Último Valor:* {ultimo_valor_formatado}"  # Valor formatado com 2 casas decimais
        f"\n*Ip:* {ip_host}"  # Emoji de telefone
        f"\n*Severidade:* {severidade_texto}"  # Emoji de alerta
    )
    # Garantir que os emotes e caracteres especiais sejam codificados corretamente
    return mensagem.encode('utf-8').decode('utf-8')

# Função para enviar mensagem no WhatsApp
def enviar_alerta_whatsapp(driver, mensagem):
    try:
        print("Aguardando o campo de mensagem...")
        message_box = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'))
        )

        driver.execute_script("arguments[0].scrollIntoView(true);", message_box)
        time.sleep(2)

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(message_box))

        actions = ActionChains(driver)
        actions.move_to_element(message_box).click().send_keys(mensagem).send_keys(Keys.RETURN).perform()

        print("Mensagem enviada com sucesso!")
        time.sleep(3)
    
    except Exception as e:
        print(f"Erro ao enviar a mensagem: {e}")

def obter_itens_do_trigger(auth_token, trigger_id):
    """Obtém os itens associados a um trigger."""
    headers = {'Content-Type': 'application/json-rpc'}
    data_trigger = {
        "jsonrpc": "2.0",
        "method": "trigger.get",
        "params": {
            "output": ["triggerid"],  # Campos do trigger que queremos
            "triggerids": trigger_id,  # ID do trigger
            "selectItems": ["itemid"]  # Seleciona os itens associados ao trigger
        },
        "auth": auth_token,
        "id": 1
    }

    try:
        response_trigger = requests.post(zabbix_url, headers=headers, data=json.dumps(data_trigger))
        if response_trigger.status_code == 200:
            response_data_trigger = response_trigger.json()
            print("Resposta da API (trigger.get):", json.dumps(response_data_trigger, indent=4))

            if 'result' in response_data_trigger and len(response_data_trigger['result']) > 0:
                items = response_data_trigger['result'][0].get('items', [])
                if items:
                    return items[0].get('itemid')  # Retorna o itemid do primeiro item associado
                else:
                    print("Nenhum item associado ao trigger.")
                    return None
            else:
                print("Erro: Resposta da API não contém o campo 'result'.")
                return None
        else:
            print(f"Erro na requisição: Status code {response_trigger.status_code}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {str(e)}")
        return None

def salvar_alerta_em_excel(alertas, nome_arquivo="alertas.xlsx"):
    """
    Salva os alertas em um arquivo Excel.
    Se o arquivo já existir, adiciona os novos alertas ao final.
    
    :param alertas: Lista de dicionários contendo os alertas.
    :param nome_arquivo: Nome do arquivo Excel (padrão: 'alertas.xlsx').
    """
    try:
        # Carrega o arquivo existente (se houver)
        df_existente = pd.read_excel(nome_arquivo)
    except FileNotFoundError:
        # Se o arquivo não existir, cria um DataFrame vazio
        df_existente = pd.DataFrame()

    # Cria um DataFrame a partir da lista de alertas
    df_novos = pd.DataFrame(alertas)

    # Concatena os DataFrames (existente + novos)
    df_final = pd.concat([df_existente, df_novos], ignore_index=True)

    # Salva o DataFrame final em um arquivo Excel
    df_final.to_excel(nome_arquivo, index=False)
    print(f"Alertas salvos em {nome_arquivo}")

# Função principal para monitorar os alertas do Zabbix
def monitorar_alertas():
    auth_token = "seutoken"
    
    alertas_enviados = set()  # Para armazenar os IDs dos alertas já enviados
    last_change_timestamp = int(time.time())  # Inicializa o timestamp com a hora atual
    alertas_para_salvar = []  # Lista para armazenar os alertas que serão salvos em Excel

    # Configurações do WebDriver
    driver_path = "/usr/local/bin/geckodriver"  # Caminho para o geckodriver
    profile_path = "/home/pedro/.mozilla/firefox/cuwiiicy.default-esr"  # Caminho para o seu perfil persistente

    options = Options()
    options.profile = profile_path  # Especificando o perfil do Firefox

    service = Service(executable_path=driver_path)
    driver = webdriver.Firefox(service=service, options=options)

    # Acessar o WhatsApp Web
    driver.get("https://web.whatsapp.com/")
    print("Escaneie o QR Code com o WhatsApp.")
    time.sleep(30)  # Aguarde o tempo necessário para escanear o QR Code
    
    group_name = "ZABBIX UAI"  # Nome do grupo no WhatsApp

    try:
        # Esperar pelo grupo
        print("Aguardando o grupo...")
        group = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, f'//span[@title="{group_name}"]'))
        )
        
        group.click()

        while True:
            print("Verificando por novos alertas...")

            # Consultar alertas com base no último timestamp (last_change_timestamp)
            alerts = obter_alertas_zabbix(auth_token, last_change_timestamp)

            if alerts:
                for alert in alerts:
                    alert_id = int(alert['triggerid'])
                    last_change = int(alert['lastchange'])
                    
                    # Verifique se o lastchange do alerta é maior que o last_change_timestamp
                    if last_change > last_change_timestamp:
                        # Obter o itemid associado ao trigger
                        item_id = obter_itens_do_trigger(auth_token, alert_id)
                        if item_id:
                            # Obter o último valor do item
                            item = obter_ultimo_valor_item(auth_token, item_id)
                            if item:
                                # Formatar a mensagem de alerta
                                mensagem_alerta = formatar_mensagem_alerta(alert, auth_token, item)
                                print(f"Novo alerta encontrado: {alert['description']} (EventID: {alert_id})")
                                
                                # Adicionar o alerta à lista de alertas para salvar em Excel
                                alertas_para_salvar.append({
                                    "EventID": alert_id,
                                    "Descrição": alert['description'].replace('{HOST.NAME}', ''),
                                    "Host": alert['hosts'][0]['name'] if alert.get('hosts') else "N/A",
                                    "IP": obter_ip_do_host(auth_token, alert['hosts'][0]['hostid']) if alert.get('hosts') else "N/A",
                                    "Último Valor": item.get('lastvalue', 'N/A'),
                                    "Severidade": alert.get('priority', 'N/A'),
                                    "Data": datetime.fromtimestamp(int(alert['lastchange'])).strftime('%Y-%m-%d %H:%M:%S'),
                                    "Status": "Resolvido" if alert.get('value') == "0" else "Não Resolvido"
                                })

                                # Enviar a mensagem de alerta
                                enviar_alerta_whatsapp(driver, mensagem_alerta)
                                alertas_enviados.add(alert_id)  # Marcar o alerta como enviado
                                last_change_timestamp = last_change  # Atualiza o timestamp da última mudança
                        else:
                            print(f"Nenhum item associado ao trigger {alert_id}.")
            else:
                print("Nenhum alerta novo encontrado.")
            
            # Salvar os alertas em Excel a cada iteração (ou em um intervalo específico)
            if alertas_para_salvar:
                salvar_alerta_em_excel(alertas_para_salvar, "alertas.xlsx")
                alertas_para_salvar = []  # Limpa a lista após salvar

            time.sleep(5)  # Verificar a cada 5 segundos

    except Exception as e:
        print(f"Erro ao enviar a mensagem ou ao acessar o WhatsApp Web: {e}")

    # Salvar os alertas restantes antes de encerrar
    if alertas_para_salvar:
        salvar_alerta_em_excel(alertas_para_salvar, "alertas.xlsx")

    driver.quit()

# Iniciar o monitoramento
monitorar_alertas()