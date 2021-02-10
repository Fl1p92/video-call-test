from datetime import timedelta

from marshmallow import Schema, fields, ValidationError, validates, validates_schema
from marshmallow.validate import Length, Range, OneOf

from backend.db.models import CallStatus


class BaseSchema(Schema):
    id = fields.Int(validate=Range(min=0), strict=True, required=True)
    created = fields.DateTime(format='iso', required=True)


class PaymentSchema(BaseSchema):
    bill_id = fields.Int(validate=Range(min=0), strict=True, required=True)
    amount = fields.Decimal(places=2, required=True)


class BillSchema(BaseSchema):
   user_id = fields.Int(validate=Range(min=0), strict=True, required=True)
   balance = fields.Decimal(places=2, required=True)
   tariff = fields.Decimal(places=2, required=True)
   payments = fields.Nested(PaymentSchema(), many=True)


class UserSchema(BaseSchema):
    email = fields.Email(required=True)
    username = fields.Str(required=True, validate=Length(min=1, max=256))
    bill = fields.Nested(BillSchema(), required=True)


class UserCreateResponseSchema(Schema):
    data = fields.Nested(UserSchema(), required=True)
