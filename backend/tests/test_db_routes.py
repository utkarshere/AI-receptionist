from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..utils import db_utils
import datetime

router = APIRouter()


class TestBookingPayLoad(BaseModel):
    
    """
    A pydantic class to declare and validate variables for booking appointment.

    """
    user_name: str = Field(..., description="username of the user")
    user_email: str = Field(..., description="email of the user")
    appointment_datetime : str = Field(..., description="appointment date and time of the user")
    service_id : int = Field(..., description='ID of the service', ge=1)

    class Config:
        json_schema_extra = {
            "example" : {
                "user_name" : "testuser",
                "user_email" : "abc@gmail.com",
                "appointment_datetime" : "2025-10-26 10:00:00",
                "service_id" : 1
            }
        }

class ReschedulePayload(BaseModel):
    user_email: str = Field(..., description="user email address.")
    new_appointment_datetime: str = Field(..., description="2025-10-27 11:00:00")

class ModifyPayload(BaseModel):
    user_email: str = Field(..., description="user email address.")
    new_service_id: int = Field(..., description="service ID of the consulting category.")


@router.get('/services', tags = ["_TEST_Database"])
def test_get_services():
    return {"services" : db_utils.get_all_services()}

@router.get("/consultants/{service_name}", tags = ["_TEST_Database"])
def test_get_consultants(service_name: str):
    return {"service": service_name, "consultants" : db_utils.get_consultants_by_service(service_name)}

@router.get("/availability", tags = ["_TEST_Database"])
def test_check_availability():
    test_service = "Technology"
    today = datetime.date.today()
    days_until_tuesday = (1 - today.weekday() + 7)%7
    if days_until_tuesday == 0:
        days_until_tuesday = 7
    test_date = today + datetime.timedelta(days=days_until_tuesday)
    test_datetime_str = test_date.strftime(f"%Y-%m-%d 10:00:00")

    print(f"Checking availability for {test_service} on {test_datetime_str}...")
    consultants = db_utils.check_availability(test_service, test_datetime_str)

    return {
        "checking_for" : test_service,
        "at_time" : test_datetime_str,
        "available_consultants" : consultants
    }

@router.post("/book", tags = ["_TEST_Database"])
def test_book_appointment(payload: TestBookingPayLoad):
    new_appointment_id = db_utils.book_appointment(
        user_name=payload.user_name,
        user_email=payload.user_email,
        appt_datetime=payload.appointment_datetime,
        service_id=payload.service_id
    )

    if not new_appointment_id:
        raise HTTPException(status_code=400, detail="Booking failed. Slot may be unavailable")
    
    
    booking_details = db_utils.get_booking_details(new_appointment_id) #type:ignore
    return {"status" : "booked", "appointment id" : new_appointment_id, "details" : booking_details}

@router.get("/booking/{appointment_id}", tags = ["_TEST_Database"])
def test_get_booking(appointment_id: int):
    details = db_utils.get_booking_details(appointment_id)
    if not details:
        raise HTTPException(status_code=400, detail="Appointment not found")
    return details

@router.delete("/cancel/{appointment_id}", tags = ["_TEST_Database"])
def test_cancel_booking(appointment_id: int, user_email: str):
    success = db_utils.cancel_appointment(appointment_id, user_email)
    if not success:
        raise HTTPException(status_code=404, detail="Cancellation failed. Appointment not found or email mismatch.")
    return {"status": "cancelled", "appointment_id" : appointment_id}


@router.patch("/reschedule/{appointment_id}", tags=["_TEST_Database"])
def test_reschedule(appointment_id: int, payload: ReschedulePayload):
    print(f"Test: Rescheduling appointment {appointment_id}...")
    success = db_utils.reschedule_appointment(
        appointment_id, 
        payload.user_email, 
        payload.new_appointment_datetime
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Reschedule failed. The new slot may be unavailable or invalid.")
    
    return db_utils.get_booking_details(appointment_id)


@router.patch("/modify/{appointment_id}", tags=["_TEST_Database"])
def test_modify_service(appointment_id: int, payload: ModifyPayload):

    print(f"Test: Modifying service for appointment {appointment_id}...")
    success = db_utils.modify_appointment_service(
        appointment_id,
        payload.user_email,
        payload.new_service_id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Modify failed. No consultants may be available for that service at this time.")
    
  
    return db_utils.get_booking_details(appointment_id)
    
