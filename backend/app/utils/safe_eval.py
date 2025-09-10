# backend/app/utils/safe_eval.py
import ast
import operator as op

# allowed operators
OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}

def _eval(node, variables):
    if isinstance(node, ast.Expression):
        return _eval(node.body, variables)
    if isinstance(node, ast.Num):  # < Py3.8
        return node.n
    if isinstance(node, ast.Constant):  # Py3.8+
        return node.value
    if isinstance(node, ast.BinOp):
        left = _eval(node.left, variables)
        right = _eval(node.right, variables)
        op_func = OPS[type(node.op)]
        return op_func(left, right)
    if isinstance(node, ast.UnaryOp):
        return OPS[type(node.op)](_eval(node.operand, variables))
    if isinstance(node, ast.Name):
        if node.id in variables:
            return float(variables[node.id])
        raise ValueError(f"Unknown variable: {node.id}")
    raise ValueError(f"Unsupported expression node: {node}")

def safe_eval(expr: str, variables: dict):
    """Safely evaluate arithmetic expressions using variables dict."""
    parsed = ast.parse(expr, mode="eval")
    return _eval(parsed, variables)
