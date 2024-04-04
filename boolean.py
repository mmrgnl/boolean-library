import re
import boolean
from enum import Enum
import abc

def match_get_key(match):
    if match[0] is None:
        return 0
    return match[0].end()

class Token:
    def _get_hash(self): #з
        raise NotImplementedError()

class Variable(Token):
    _variable_name: str
    _negated: bool



    def negate(self):
        return Variable(self._variable_name, not self._negated)

    def __init__(self, name, negated = False):
        if negated:
            if name == "0" or name == "1":
                 self._variable_name = "0" if name == "0" else "1"
        else:
            self._variable_name = name
            self._negated = negated

    def __init__(self, string, negated = False):
        if string[0] == "~":
            if string[1] == "0" or string[1] == "1":
                self._negated = False
                if negated:
                    self._variable_name = "0" if string[1] == "0" else "1"
                else:
                    self._variable_name = string[1]
            else:
                self._variable_name = string[1:]
                self._negated = not negated
        else:
            self._variable_name = string
            self._negated = negated


    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (self._variable_name == other._variable_name and \
            self._negated == other._negated)

    def __str__(self):
        return ("~" if self._negated else "") + self._variable_name

    def _get_hash(self):
        return hash(self._variable_name) * ((int)(self._negated) + 1)

class Operator(Token):
    class _operator_enum(Enum):
        OR = 0
        AND = 1

    _type: _operator_enum
    _left_expr: Token
    _right_expr: Token

    def __init__(self, string, negated):
        if string == "+":
            self._type = self._operator_enum(negated)
        elif string == "*":
            self._type = self._operator_enum(1 - negated)
        else:
            raise ValueError("Wrong value provided to 'Operator' class")

        self._left_expr = None
        self._right_expr = None

    def __init__(self, string, left, right, negated):
        if string == "+":
            self._type = self._operator_enum(negated)
        elif string == "*":
            self._type = self._operator_enum(1 - negated)
        else:
            raise ValueError("Wrong value provided to 'Operator' class")

        self._left_expr = left
        self._right_expr = right

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        if (self._type != other._type):
            return False

        # Перестановка значений
        if (self._left_expr == other._left_expr and self._right_expr == other._right_expr):
            return True
        if (self._left_expr == other._right_expr and self._right_expr == other._left_expr):
            return True
        return False

    def negate(self):
        return None

    def __str__(self):
        return "+" if self._type == self._operator_enum.OR else "*"

    def _get_hash(self):
        return hash(self._type)


class Expression(Token):
    # Содержит разбитую на токены версию введенного уравнения(в том же порядке)
    _expression: list
    # Содержит пару: (хэш, количество токенов)
    _tokens: dict
    _arguments: list

    def redefine_expression(self, arguments: list, function: str, negated=False):
        f = Expression(arguments, function, negated)
        self._arguments = f._arguments
        self._expression = f._expression
        self._tokens = f._tokens

    def __copy__(self):
        return Expression(self._arguments, str(self), False)

    def __init__(self, arguments: list, function: str, negated=False):
        self._expression = []
        self._arguments = arguments
        self._tokens = {}

        # if not self.__check_input(function, arguments):
        #     raise ValueError("Error in provided function string")

        function = function.replace(" ", "")

        var = r"(~)?[01{args}]".format(args = ''.join(re.escape(s) for s in arguments))
        bracket = r"(~)?\(.+?\)"
        operator = r"[\*\+]"

        cursor = 0

        while cursor < len(function):
            var_match = re.match(var, function[cursor:])
            bracket_match = re.match(bracket, function[cursor:])
            operator_match = re.match(operator, function[cursor:])

            longest_match = sorted(
                [
                    (var_match, Variable),
                    (bracket_match, Expression),
                    (operator_match, Operator)
                ],
                key=match_get_key, reverse=True)[0]
            if longest_match[0] is None:
                raise ValueError("Error while splitting function into tokens")

            # Различные аргументы для вызова конструктора
            if longest_match[1] is Variable:
                token = longest_match[1](longest_match[0][0], negated)
            elif longest_match[1] is Expression:
                if longest_match[0][0][0] == "~":
                    token = longest_match[1](arguments, longest_match[0][0][2:-1], negated=True)
                else:
                    token = longest_match[1](arguments, longest_match[0][0][1:-1])
            else:
                token = longest_match[1](longest_match[0][0], self._expression[-1], None, negated)

            # Закончили формировать instance оператора
            if len(self._expression) > 0 and type(self._expression[-1]) is Operator:
                self._expression[-1]._right_expr = token
            self._expression.append(token)

            token_hash = token._get_hash()
            # Если токен уже существует в словаре, прибавить, в противном случае token = 1
            self._tokens[token_hash] = self._tokens.get(token_hash, 0) + 1

            cursor += longest_match[0].end()

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        if self._get_hash() != other._get_hash():
            return False

        #Сравнение всех операторов отдельно
        self_operators = [token for token in self._expression if type(token) is Operator]
        other_operators = [token for token in other._expression if type(token) is Operator]

        for self_op in self_operators:
            op_match = False
            for other_op in other_operators:
                if self_op == other_op:
                    op_match = True
                    break
            if not op_match:
                return False
        return True

    def __str__(self):
        string = ""
        for token in self._expression:
            if type(token) == self.__class__:
                string += "(" + str(token) + ")"
            else:
                string += str(token)
        return string

    def negate(self):
        return Expression(self._arguments, str(self), True)

    def simplify(self):
        #TODO

        for token in self._expression:
            if type(token) is Expression:
                token.simplify()

        expr = []
        current = []
        for token in self._expression:
            if type(token) is Operator:
                if token._type == Operator._operator_enum.AND:
                    if len(current) == 0:
                        current.extend([token._left_expr, token._right_expr])
                    else:
                        current.append(token._right_expr)
                else:
                    if len(current) >= 3:
                        expr.append(current)
                        expr.append(token)
                        current = []
                    else:
                        expr.extend([token._left_expr, token])
        if len(current) > 0:
            expr.append(current)
        else:
            expr.append(self._expression[-1])

        for mul_expr in expr:
            if type(mul_expr) != list:
                continue
            mark_delete = []
            for _mul_token_a in range(len(mul_expr)):
                for _mul_token_b in range(_mul_token_a + 1, len(mul_expr)):
                    if (mul_expr[_mul_token_a] == mul_expr[_mul_token_b]):
                        self.__reduce([mul_expr[_mul_token_b]], [None])
                        mark_delete.append(mul_expr[_mul_token_b])
                    elif (mul_expr[_mul_token_a] == mul_expr[_mul_token_b].negate()):
                        self.__reduce(mul_expr, [None for i in range(len(mul_expr))])
                        mark_delete.extend(mul_expr)
            for to_delete in mark_delete:
                mul_expr.remove(to_delete)

        new_expr = []
        for mul_expr in expr:
            if type(mul_expr) != list:
                new_expr.append(mul_expr)
                continue
            if len(mul_expr) != 0:
                if len(mul_expr) == 1:
                    new_expr.append(mul_expr[0])
                else:
                    new_expr.append(mul_expr)
            else:
                if len(new_expr) > 0:
                    new_expr.pop()
        expr = new_expr

        if len(expr) == 0:
            self._expression.append(Variable("0"))
            return

        while True:
            to_break = False
            for tk1 in range(len(expr)):
                if type(expr[tk1]) is Operator:
                    continue
                for tk2 in range(tk1 + 1, len(expr)):
                    if type(expr[tk2]) is list:
                        if type(expr[tk1]) is not list:
                            continue
                        if sorted(expr[tk1]) == sorted(expr[tk2]):
                            self.__reduce(expr[tk2], [None for i in range(len(mul_expr))])
                            expr.pop(tk2)
                            to_break = True
                            break
                    else:
                        if expr[tk1] == expr[tk2]:
                            self.__reduce([expr[tk2]], [None])
                            expr.pop(tk2)
                            to_break = True
                            break
                        if expr[tk1] == expr[tk2].negate():
                            self.__reduce([expr[tk1], expr[tk2]], [Variable("1"), None])
                            expr.pop(tk2)
                            expr.pop(tk2 - 1)
                            expr[tk1] = Variable("1")
                            to_break = True
                            break
                if to_break:
                    break
            if not to_break:
                break


    def _contains(self, token):
        for tk in self._expression:
            if tk == token:
                return tk
        return None

    def __reduce(self, to_delete: list, to_insert: list):
        if len(to_delete) != len(to_insert):
            raise ValueError("Lists do not match in size")

        new_exp = []
        for token in self._expression:
            should_delete = -1
            if type(token) is Operator:
                new_exp.append(token)
                continue
            for i in range(len(to_delete)):
                if token is to_delete[i]:
                    should_delete = i
                    break
            if should_delete >= 0:
                # If not null
                if to_insert[should_delete] is None:
                    # Remove last iterator
                    if len(new_exp) > 0:
                        new_exp.pop()
                else:
                    new_exp.append(to_insert[should_delete])
            else:
                new_exp.append(token)
        if len(new_exp) > 0 and new_exp[-1] is None:
            new_exp.pop()
            new_exp.pop()

        # Обновление операторов
        for i in range(len(new_exp)):
            if type(new_exp[i]) is Operator:
                new_exp[i]._left_expr = new_exp[i - 1]
                new_exp[i]._right_expr = new_exp[i + 1]
        self._expression = new_exp

    def __len__(self):
        return len(self._expression)

    def evaluate(self, arguments: list):
        function = str(self)
        for var in range(len(arguments)):
            function = function.replace(self._arguments[var], str(arguments[var]))
        function = function.replace("~", "not ")
        function = function.replace("+", " or ")
        function = function.replace("*", " and ")

        return bool(eval(function))

    def _get_hash(self):
        return sum(self._tokens.keys())

if __name__ == "__main__":
    func1 = Expression(["x", "y", "z"], "x*y*x + x*z*~x + x + ~y")
    func1.simplify()
    print(func1)
    print(func1.evaluate([0, 0, 0]), "\n")

    func2 = Expression(["x", "y"], "(x+y)*~(x+y)")
    func2.simplify()
    print(func2)
    print(func2.evaluate([0, 1]), "\n")

    func3 = Expression(["x", "y"], "(x*y*x)+(x*y)")
    func3.simplify()
    print(func3)
    print(func3.evaluate([0, 1]), "\n")

    func4 = Expression(["x", "y"], "(x*y*x)+~(x*y)")
    func4.simplify()
    print(func4)

    func5 = Expression(["x", "y"], "(x*y*x)+~(x*y)")
    print("original: ", func5)
    func5.redefine_expression(["x", "y", "z"], "x*y*x + x*z*~x + x + ~y")
    print("overriden: ", func5)
    func5.simplify()
    print("simplified:", func5)
