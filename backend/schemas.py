from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Number = Annotated[str, StringConstraints(min_length=1, max_length=32)]
Identifier = Annotated[int, Field(strict=True, gt=0)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Farmer(Input):
    name: Text
    phone: Text
    village: Text
    bank_reference: Annotated[str, StringConstraints(max_length=120)] = ""


class Crop(Input):
    name: Text
    grades: Annotated[list[Text], Field(min_length=1, max_length=20)]
    threshold: Number
    max_moisture: Number


class Price(Input):
    crop_id: Identifier
    grade: Text
    price: Number
    effective_from: Text


class Advance(Input):
    farmer_id: Identifier
    amount: Number
    given_on: Text


class Delivery(Input):
    farmer_id: Identifier
    crop_id: Identifier
    grade: Text
    gross_kg: Number
    moisture: Number
    delivered_on: Text


class Correction(Input):
    amount: Number
    delivered_on: Text
    reason: Text


class Payout(Input):
    farmer_id: Identifier
    week: Text
