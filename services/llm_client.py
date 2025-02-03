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
        
        prompt = f"""Analiza el siguiente mensaje financiero y devuelve la respuesta en JSON: '{message}'

Categorías existentes: [{categories_str}]

Para CONSULTAS (resumen, balance, etc) usar este formato:
{{
    "type": "query",
    "query_type": "summary"|"balance",  # "summary" para "resumen", "mostrame todo" | "balance" para "cuánto tengo"
    "money_type": "cash"|"bank"|"all"   # "cash" para efectivo, "bank" para banco, "all" para todo
}}

Para TRANSACCIONES usar este formato (siempre en array):
[
    {{
        "type": "expense"|"income",
        "amount": float,
        "description": string,
        "money_type": "bank"|"cash",
        "category": string,
        "should_create_category": boolean,
        "category_reason": string
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
    "exchange_rate": float  # Calculado como target_amount/amount
}}

REGLAS:
1. Si el mensaje es una consulta como "resumen", "balance", "cuánto tengo", "mostrame" → Usar formato de CONSULTAS
2. Si el mensaje es sobre gastos/ingresos → Usar formato de TRANSACCIONES
3. Si el mensaje es sobre cambio de divisas → Usar formato de CAMBIO
4. Para pagos de tarjeta de crédito o servicios financieros → category: "financiero"
5. Para transferencias o tarjeta → money_type: "bank"
6. Para efectivo → money_type: "cash"
7. Convertir TODOS los montos a números (sin el símbolo $)
8. NO incluir texto fuera de la estructura JSON
9. NO usar caracteres especiales en las descripciones

Ejemplos:
1. "Dame un resumen" →
{{
    "type": "query",
    "query_type": "summary",
    "money_type": "all"
}}

2. "Gasté $100 en comida" →
[{{
    "type": "expense",
    "amount": 100.0,
    "description": "Comida",
    "money_type": "cash",
    "category": "comida",
    "should_create_category": false,
    "category_reason": ""
}}]

3. "Cambié 100 USD a 90000 pesos" →
{{
    "type": "exchange",
    "amount": 100.0,
    "target_amount": 90000.0,
    "source_currency": "USD",
    "target_currency": "ARS",
    "money_type": "cash",
    "exchange_rate": 900.0
}}

Palabras clave:
- Consultas: "resumen", "balance", "cuánto tengo", "mostrar", "dame"
- Gastos: "gasté", "pagué", "compré", "tarjeta"
- Ingresos: "cobré", "recibí", "ingresé", "deposité"
- Cambios: "cambié", "convertí", "pasé de"
"""

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