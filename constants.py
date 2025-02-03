class TransactionType:
    EXPENSE = "expense"
    INCOME = "income"
    EXCHANGE = "exchange"

    @classmethod
    def values(cls):
        return [cls.EXPENSE, cls.INCOME, cls.EXCHANGE]


class MoneyType:
    CASH = "cash"
    BANK = "bank"


class Category:
    COMIDA = "comida"
    TRANSPORTE = "transporte"
    SERVICIOS = "servicios"
    SUPERMERCADO = "supermercado"
    ENTRETENIMIENTO = "entretenimiento"
    SALUD = "salud"
    OTROS = "otros"
    EXCHANGE = "exchange" 