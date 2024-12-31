
from enum import Enum


class TokenType(Enum):
    VAR = 1
    OPERATOR = 2
    NUMBER = 3
    PARENTHESES = 4

class Token():
    def __init__(self, token_type, value):
        self.token_type = token_type
        self.value = value

    def __repr__(self):
        return f"{self.token_type}({self.value})"
    
    def __eq__(self, compr):
        if self.value == compr.value and self.token_type == compr.token_type:
            return True
        return False

    @staticmethod
    def var(value):
        return Token(TokenType.VAR, value)
    
    @staticmethod
    def operator(value):
        return Token(TokenType.OPERATOR, value)

    @staticmethod
    def number(value):
        return Token(TokenType.NUMBER, value)

    @staticmethod
    def parentheses(value):
        return Token(TokenType.PARENTHESES, value)

    @staticmethod
    def parse_expr(expr):
        current_var = ""
        numeric = ""
        for i in expr:
            if current_var:
                if i in ['\t', '\n', ' ']:
                    continue
                elif i in ['+', '-', '*', '/']:
                    yield Token.var(current_var)
                    yield Token.operator(i)
                    current_var = ""
                    continue
                elif i in ['(', ')']:
                    yield Token.var(current_var)
                    yield Token.parentheses(i)
                    current_var = ""
                else:
                    current_var += i
            elif numeric:
                if i in ['\t', '\n', ' ']:
                    continue
                elif i in ['+', '-', '*', '/']:
                    yield Token.number(numeric)
                    yield Token.operator(i)
                    numeric = ""
                    continue
                elif i in ['(', ')']:
                    yield Token.number(numeric)
                    yield Token.parentheses(i)
                    numeric = ""
                else:
                    numeric += i
            elif i in ['+', '-', '*', '/']:
                yield Token.operator(i)
            elif i in ['(', ')']:
                yield Token.parentheses(i)
            elif i.isalpha():
                current_var = i
            elif i.isnumeric():
                numeric = i
        if current_var:
            yield Token.var(current_var)
        if numeric:
            yield Token.number(numeric)

