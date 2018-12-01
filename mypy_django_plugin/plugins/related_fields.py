import typing
from typing import Optional, cast

from mypy.checker import TypeChecker
from mypy.nodes import StrExpr
from mypy.plugin import FunctionContext
from mypy.types import Type, CallableType, Instance, AnyType, TypeOfAny

from mypy_django_plugin import helpers


def reparametrize_with(instance: Instance, new_typevars: typing.List[Type]):
    return Instance(instance.type, args=new_typevars)


def fill_typevars_with_any(instance: Instance) -> Type:
    return reparametrize_with(instance, [AnyType(TypeOfAny.unannotated)])


def get_valid_to_value_or_none(ctx: FunctionContext) -> Optional[Instance]:
    if 'to' not in ctx.arg_names:
        # shouldn't happen, invalid code
        ctx.api.msg.fail(f'to= parameter must be set for {ctx.context.callee.fullname}',
                         context=ctx.context)
        return None

    arg_type = ctx.arg_types[ctx.arg_names.index('to')][0]
    if not isinstance(arg_type, CallableType):
        to_arg_expr = ctx.args[ctx.arg_names.index('to')][0]
        if not isinstance(to_arg_expr, StrExpr):
            # not string, not supported
            return None
        model_info = helpers.get_model_type_from_string(to_arg_expr,
                                                        all_modules=cast(TypeChecker, ctx.api).modules)
        if model_info is None:
            return None
        return Instance(model_info, [])

    referred_to_type = arg_type.ret_type
    for base in referred_to_type.type.bases:
        if base.type.fullname() == helpers.MODEL_CLASS_FULLNAME:
            break
    else:
        ctx.api.msg.fail(f'to= parameter value must be '
                         f'a subclass of {helpers.MODEL_CLASS_FULLNAME}',
                         context=ctx.context)
        return None

    return referred_to_type


def extract_to_parameter_as_get_ret_type_for_related_field(ctx: FunctionContext) -> Type:
    referred_to_type = get_valid_to_value_or_none(ctx)
    if referred_to_type is None:
        # couldn't extract to= value
        return fill_typevars_with_any(ctx.default_return_type)
    return reparametrize_with(ctx.default_return_type, [referred_to_type])