from marshmallow import Schema, fields
from marshmallow.validate import Length, Range, OneOf

from backend.db.models import CallStatus


class BaseSchema(Schema):
    id = fields.Int(validate=Range(min=0), strict=True)
    created = fields.DateTime(format='iso')


class CallSchema(BaseSchema):
    caller_id = fields.Int(validate=Range(min=0), strict=True, required=True)
    callee_id = fields.Int(validate=Range(min=0), strict=True, required=True)
    duration = fields.Int(validate=Range(min=0), strict=True)
    status = fields.Str(validate=OneOf([status.name for status in CallStatus]))


class PaymentSchema(BaseSchema):
    bill_id = fields.Int(validate=Range(min=0), strict=True, required=True)
    amount = fields.Decimal(validate=Range(min=0, min_inclusive=False), places=2, required=True)


class BillSchema(BaseSchema):
    user_id = fields.Int(validate=Range(min=0), strict=True, required=True)
    balance = fields.Decimal(places=2)
    tariff = fields.Decimal(validate=Range(min=0, min_inclusive=False), places=2, required=True)


class UserSchema(BaseSchema):
    email = fields.Email(required=True)
    username = fields.Str(required=True, validate=Length(min=1, max=256))
    password = fields.Str(required=True, validate=Length(min=7), load_only=True)


class UserPatchSchema(BaseSchema):
    email = fields.Email()
    username = fields.Str(validate=Length(min=1, max=256))


class JWTTokenSchema(Schema):
    token = fields.Str(required=True)
    user = fields.Nested(UserSchema(only=('id', 'email', 'username')))


class BillDetailsSchema(BillSchema):
    max_call_duration_minutes = fields.Int(strict=True)


class UserDetailsResponseSchema(Schema):
    data = fields.Nested(UserSchema(exclude=('password', )), required=True)


class JWTTokenResponseSchema(Schema):
    data = fields.Nested(JWTTokenSchema(), required=True)


class UserListResponseSchema(Schema):
    data = fields.Nested(UserSchema(exclude=('password', ), many=True), required=True)


class NoContentResponseSchema(Schema):
    pass


class BillDetailsResponseSchema(Schema):
    data = fields.Nested(BillDetailsSchema(), required=True)


class PaymentDetailsResponseSchema(Schema):
    data = fields.Nested(PaymentSchema(), required=True)


class PaymentListResponseSchema(Schema):
    data = fields.Nested(PaymentSchema(many=True), required=True)


class CallDetailsResponseSchema(Schema):
    data = fields.Nested(CallSchema(), required=True)


class CallListResponseSchema(Schema):
    data = fields.Nested(CallSchema(many=True), required=True)
