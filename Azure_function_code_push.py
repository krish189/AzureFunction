
"""Module docstring goes here."""
  
import logging
import os
import azure.functions as func
from azure.cosmos import CosmosClient
import json
import requests 
import socket
import uuid


"""Azue Cosmos DB creds """
URL = os.environ['Cloudmon_push_url']
KEY = os.environ['Cloudmon_push_key']
client = CosmosClient(URL, credential=KEY)
DATABASE_NAME = 'cloudmon-push'
database = client.get_database_client(DATABASE_NAME)
CONTAINER_NAME = 'cloudmon-mobile-push'
container = database.get_container_client(CONTAINER_NAME)


def send_to_onesignal(tag_one,alert_data): 
    logging.info(str(alert_data))
    logging.info(tag_one)
    header= { 
    "Authorization": "Basic Y2RiNDFjNGEtMGY3MC00NDE4LWFkMDEtMTc1MTY5MDI5OTE5" ,
    'content-type': 'application/json'
    } 
    payload = { 
    "app_id": "e450a9a3-02ac-4129-b187-851a0e946c1f", 
    'filters': [
        {"field": "tag", "key": "controller-url", "relation": "=", "value": tag_one}
    ],
    "contents": {"en": str(alert_data)} 
    } 
    response = requests.post("https://onesignal.com/api/v1/notifications", headers=header, data=json.dumps(payload)) 
    if response.status_code == 200:
        logging.info("Message sent successfully")
    else: 
        logging.error("Error sending message: " + response.text)
    logging.info(response.json())
    

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Webhook received a request.')

    req_body = req.get_body()
    logging.info(req_body)
    
    data = json.loads(req_body)
    
    if data.get('title',None):
        title = data.get('title',None)
        sliced_title = title.split("for")[0].strip()
        bullets=data.get("bullets",None)
        modify_title=sliced_title.replace("Cloudmon Alert",bullets[2]["value"])
        logging.info(bullets[2]["value"])
        logging.info(modify_title)
        headers = dict(req.headers.items())
        logging.info(headers)
        ip = headers['x-forwarded-for']
        host_ip = ip.split(":") 
        Host_ip = host_ip[0]
        logging.info(Host_ip)
        query="SELECT * FROM c"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        for item in items:
            if "Controller_ip" in item and item["Controller_ip"] == Host_ip:
                if "Tag" in item:
                    tags=str(item["Tag"])
                    query = "SELECT * FROM c WHERE c.Controller_ip = @controller_ip"
                    params = [{'name': '@controller_ip', 'value': Host_ip}]
                    result = container.query_items(query=query, parameters=params, enable_cross_partition_query=True)
                    for item in result:
                        item['Host_ip'] = Host_ip
                        container.upsert_item(item)
                else:
                    logging.info("Item with matching Controller_ip does not have a Tag property")
            else:
                logging.info("Item does not have matching Controller_ip")

        logging.info(tags)  
        send_to_onesignal(tags,modify_title)
    else:
        
        c_url = data.get('url',None)
        logging.info(c_url)

        c_ip = socket.gethostbyname(c_url)
        logging.info(c_ip)
        
        message = data.get('message',None)
        logging.info(message)
        
        c_tag = data.get('controller-tag',None)
        logging.info(c_tag)
        
        time = data.get('time',None)
        logging.info(time)
        
        container.upsert_item({
        'id': str(uuid.uuid4()),
        'Controller_url': c_url,
        'Controller_ip': c_ip,
        'Message':message,
        'Time':time,
        'Tag':c_tag
                }
            )

    response = {
        "status": "success"
    }
    logging.info(data)


    return func.HttpResponse(json.dumps(response), status_code=200)