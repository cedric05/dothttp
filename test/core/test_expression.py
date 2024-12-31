import pytest
from dothttp.parse.expression import Token, TokenType

def test_var_token():
    token = Token.var("x")
    assert token.token_type == TokenType.VAR
    assert token.value == "x"

def test_operator_token():
    token = Token.operator("+")
    assert token.token_type == TokenType.OPERATOR
    assert token.value == "+"

def test_number_token():
    token = Token.number("123")
    assert token.token_type == TokenType.NUMBER
    assert token.value == "123"

def test_parentheses_token():
    token = Token.parentheses("(")
    assert token.token_type == TokenType.PARENTHESES
    assert token.value == "("

def test_parse_expr_simple():
    expr = "x + 1"
    tokens = list(Token.parse_expr(expr))
    print(tokens)
    assert tokens == [
        Token.var("x"),
        Token.operator("+"),
        Token.number("1")
    ]

def test_parse_expr_with_parentheses():
    expr = "(x + 1) * y"
    tokens = list(Token.parse_expr(expr))
    assert tokens == [
        Token.parentheses("("),
        Token.var("x"),
        Token.operator("+"),
        Token.number("1"),
        Token.parentheses(")"),
        Token.operator("*"),
        Token.var("y")
    ]

def test_parse_expr_with_spaces():
    expr = "  x   +  1 "
    tokens = list(Token.parse_expr(expr))
    assert tokens == [
        Token.var("x"),
        Token.operator("+"),
        Token.number("1")
    ]

def test_parse_expr_with_multiple_digits():
    expr = "x + 123"
    tokens = list(Token.parse_expr(expr))
    assert tokens == [
        Token.var("x"),
        Token.operator("+"),
        Token.number("123")
    ]

def test_parse_expr_with_multiple_vars():
    expr = "x + y"
    tokens = list(Token.parse_expr(expr))
    assert tokens == [
        Token.var("x"),
        Token.operator("+"),
        Token.var("y")
    ]

def test_parse_expr_edge_case_empty():
    expr = ""
    tokens = list(Token.parse_expr(expr))
    assert tokens == []

def test_parse_expr_edge_case_only_operators():
    expr = "+-*/"
    tokens = list(Token.parse_expr(expr))
    assert tokens == [
        Token.operator("+"),
        Token.operator("-"),
        Token.operator("*"),
        Token.operator("/")
    ]

def test_parse_expr_edge_case_only_parentheses():
    expr = "()"
    tokens = list(Token.parse_expr(expr))
    assert tokens == [
        Token.parentheses("("),
        Token.parentheses(")")
    ]