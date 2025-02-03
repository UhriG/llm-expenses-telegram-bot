import os
import json
from typing import Dict, Any
from utils.logger import logger
from ollama import Client

class LLMClient:
    def __init__(self, transaction_service):
        self.host = os.getenv('OLLAMA_HOST')
        self.model = os.getenv('MODEL')
        self.client = Client(host=self.host)
        self.transaction_service = transaction_service

    def get_response(self, prompt: str) -> Dict[str, Any]:
        """Get structured response from LLM using JSON mode."""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt + "\nRespond ONLY with valid JSON.",
                system="You are a financial assistant that ONLY responds in valid JSON format.",
                format="json",
                stream=False,
                options={
                    'temperature': 0.7,
                    'num_predict': 100,
                }
            )
            
            # Log the raw response
            logger.info(f"Raw model response: {response['response']}")
            
            # Response will be a valid JSON string
            try:
                return json.loads(response['response'])
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in response: {e}")
                logger.error(f"Problematic response: {response['response']}")
                return None
            
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            logger.error(f"Full error details: {str(e)}")
            return None

    def get_structured_response(self, message: str) -> Dict[str, Any]:
        """Get a structured response with specific format."""
        # Get existing categories from database
        existing_categories = self.transaction_service.db.get_all_categories()
        categories_str = ", ".join(f'"{cat}"' for cat in existing_categories)
        
        # Clean up the message - replace multiple newlines with a single one
        message = ' '.join(message.split())
        
        prompt = f'''Analiza el siguiente mensaje financiero y devuelve la respuesta en JSON: '{message}'

Categorías existentes: [{categories_str}]

REGLAS PARA CATEGORÍAS:
1. Para gastos en alimentos (fiambrería, carnicería, verdulería) usar "supermercado"
2. Para gastos de alquiler usar "alquiler"
3. Para gastos de transporte (nafta, subte, colectivo) usar "transporte"
4. Para gastos de entretenimiento (cine, teatro, salidas) usar "entretenimiento"
5. Para gastos de salud (medicamentos, consultas) usar "salud"
6. Para gastos de educación (cursos, libros) usar "educación"
7. Para gastos de ropa y calzado usar "ropa"
8. Para gastos de servicios (luz, gas, internet, seguro, monotributo, etc) usar "servicios"
9. Para pagos de tarjetas usar "tarjetas"
10.Para gastos de delivery, pedidos ya, rappi, etc usar "delivery"
11. Para gastos de vicios (tabaco, alcohol, drogas) usar "vicios"
12. Si no hay una categoría apropiada, crear una nueva categoría en base a la descripción del gasto

Ejemplos:
1. "Gasté 10000 en fiambrería" →
[{{
    "type": "expense",
    "amount": 10000.0,
    "description": "Fiambreria",
    "money_type": "cash",
    "category": "supermercado",
    "should_create_category": false,
    "category_reason": "",
    "currency": "ARS"
}}]

2. "Pagué el alquiler $50000" →
[{{
    "type": "expense",
    "amount": 50000.0,
    "description": "Alquiler",
    "money_type": "bank",
    "category": "alquiler",
    "should_create_category": false,
    "category_reason": "",
    "currency": "ARS"
}}]

3. "Compré carne en la carnicería $15000" →
[{{
    "type": "expense",
    "amount": 15000.0,
    "description": "Carniceria",
    "money_type": "cash",
    "category": "supermercado",
    "should_create_category": false,
    "category_reason": "",
    "currency": "ARS"
}}]

Para CONSULTAS (resumen, balance, etc) usar este formato:
{{
    "type": "query",
    "query_type": "summary"|"balance",
    "money_type": "cash"|"bank"|"all"
}}

Para TRANSACCIONES usar este formato (siempre en array):
[
    {{
        "type": "expense"|"income",  # IMPORTANTE: Solo "expense" o "income" son válidos
        "amount": float,
        "description": string,
        "money_type": "bank"|"cash",
        "category": string,
        "should_create_category": boolean,
        "category_reason": string,
        "currency": string
    }}
]

Para CAMBIO DE DIVISAS usar este formato:
{{
    "type": "exchange",
    "amount": float,
    "target_amount": float,
    "source_currency": string,
    "target_currency": string,
    "money_type": "bank"|"cash",
    "exchange_rate": float # IMPORTANTE: Debe ser el resultado de la division entre el target_amount y el 
    source_amount
}}

REGLAS:
1. Si el mensaje es una consulta como "resumen", "balance", "cuánto tengo", "mostrame" → type: "query"
2. Si el mensaje es sobre gastos → type: "expense"
3. Si el mensaje es sobre ingresos → type: "income"
4. Si el mensaje es sobre cambio de divisas → type: "exchange"
5. Para transferencias o tarjeta → money_type: "bank"
6. Para efectivo → money_type: "cash"
7. Convertir TODOS los montos a números (sin el símbolo $)
8. NO incluir texto fuera de la estructura JSON
9. NO usar caracteres especiales en las descripciones
10. Para moneda usar "ARS" o "USD" (default: "ARS")

'''

        try:
            response = self.get_response(prompt)
            if not response:
                return None
            
            # If response is a transaction dict, wrap it in a list
            if isinstance(response, dict):
                if response.get('type') in ['expense', 'income']:
                    response = [response]
            
            return response
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return None 