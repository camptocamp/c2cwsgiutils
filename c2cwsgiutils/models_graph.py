import inspect
import sys
from typing import Any, List, Set

import sqlalchemy as sa


def generate_model_graph(module: Any) -> None:
    if len(sys.argv) == 1:
        base_name = "Base"
    elif len(sys.argv) == 2:
        base_name = sys.argv[1]
    else:
        print("Invalid parameters\nUsage: %s [base_class]" % sys.argv[0])
        sys.exit(1)

    _generate_model_graph(module, getattr(module, base_name))


def _generate_model_graph(module: Any, base: Any) -> None:
    print(
        """
    digraph {
        rankdir=BT;
    """
    )

    interesting = {
        getattr(module, symbol_name)
        for symbol_name in dir(module)
        if _is_interesting(getattr(module, symbol_name), base)
    }

    for symbol in list(interesting):
        symbol = getattr(module, symbol.__name__)
        if _is_interesting(symbol, base):
            _print_node(symbol, interesting)

    print("}")


def _print_node(symbol: Any, interesting: Set[Any]) -> None:
    print('%s [label="%s", shape=box];' % (symbol.__name__, _get_table_desc(symbol)))
    for parent in symbol.__bases__:
        if parent != object:
            if parent not in interesting:
                _print_node(parent, interesting)
                interesting.add(parent)
            print("%s -> %s;" % (symbol.__name__, parent.__name__))


def _is_interesting(what: Any, base: type) -> bool:
    return inspect.isclass(what) and issubclass(what, base)


def _get_table_desc(symbol: Any) -> str:
    cols = [symbol.__name__, ""] + _get_local_cols(symbol)

    return "\\n".join(cols)


def _get_all_cols(symbol: Any) -> List[str]:
    cols = []

    for member_name in symbol.__dict__:
        member = getattr(symbol, member_name)
        if member_name in ("__table__", "metadata"):
            # Those are not fields
            pass
        elif isinstance(member, sa.sql.schema.SchemaItem):
            cols.append(member_name + ("[null]" if member.nullable else ""))
        elif isinstance(member, sa.orm.attributes.InstrumentedAttribute):
            nullable = (
                member.property.columns[0].nullable
                if isinstance(member.property, sa.orm.ColumnProperty)
                else False
            )
            link = not isinstance(member.property, sa.orm.ColumnProperty)
            cols.append(member_name + (" [null]" if nullable else "") + (" ->" if link else ""))

    return cols


def _get_local_cols(symbol: Any) -> List[str]:
    result = set(_get_all_cols(symbol))
    for parent in symbol.__bases__:
        result -= set(_get_all_cols(parent))

    return sorted(list(result))
