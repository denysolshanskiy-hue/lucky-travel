from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from supabase import create_client, Client


@dataclass
class Tour:
    id: int
    title: str
    starts_at: str
    adult_price: int
    child_price: int
    prepay: int | None
    seats_total: int
    kind: str
    photo_file_id: str | None
    included: str
    route: str
    payment_url: str | None
    instructor_contact: str | None
    car_number: str | None
    is_active: int
    created_at: str | None = None


@dataclass
class Booking:
    id: int
    tour_id: int
    user_id: int
    username: str | None
    full_name: str
    phone: str
    people_count: int
    ages: str
    status: str
    created_at: str
    reminder_3d_sent: int
    reminder_1d_sent: int
    tour_title: str | None = None
    starts_at: str | None = None


@dataclass
class CampingBooking:
    id: int
    user_id: int
    username: str | None
    full_name: str
    phone: str
    option_code: str
    option_title: str
    item_type: str
    item_number: int
    units: int
    status: str
    created_at: str
    booking_date: str | None = None


@dataclass
class RentalBooking:
    id: int
    user_id: int
    username: str | None
    full_name: str
    phone: str
    rental_title: str
    rental_price: int
    status: str
    created_at: str
    booking_date: str | None = None


class Database:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)

    async def init(self) -> None:
        """Initialize database - tables should be created in Supabase dashboard"""
        pass

    async def create_tour(self, data: dict) -> int:
        response = self.client.table("tours").insert({
            "title": data["title"],
            "starts_at": data["starts_at"],
            "adult_price": data["adult_price"],
            "child_price": data["child_price"],
            "prepay": data.get("prepay"),
            "seats_total": data["seats_total"],
            "kind": data["kind"],
            "photo_file_id": data.get("photo_file_id"),
            "included": data["included"],
            "route": data["route"],
            "payment_url": data.get("payment_url"),
            "instructor_contact": data.get("instructor_contact"),
            "car_number": data.get("car_number"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }).execute()
        return int(response.data[0]["id"])

    async def list_active_tours(self) -> list[Tour]:
        response = self.client.table("tours").select("*").eq(
            "is_active", 1
        ).order("starts_at", desc=False).execute()
        return [Tour(**row) for row in response.data]

    async def list_inactive_tours(self) -> list[Tour]:
        response = self.client.table("tours").select("*").eq(
            "is_active", 0
        ).order("starts_at", desc=True).execute()
        return [Tour(**row) for row in response.data]

    async def get_tour(self, tour_id: int) -> Tour | None:
        response = self.client.table("tours").select("*").eq(
            "id", tour_id
        ).execute()
        if response.data:
            return Tour(**response.data[0])
        return None

    async def deactivate_tour(self, tour_id: int) -> bool:
        response = self.client.table("tours").update(
            {"is_active": 0}
        ).eq("id", tour_id).execute()
        return len(response.data) > 0

    async def activate_tour(self, tour_id: int) -> bool:
        response = self.client.table("tours").update(
            {"is_active": 1}
        ).eq("id", tour_id).execute()
        return len(response.data) > 0

    async def create_booking(self, data: dict) -> int:
        response = self.client.table("bookings").insert({
            "tour_id": data["tour_id"],
            "user_id": data["user_id"],
            "username": data.get("username"),
            "full_name": data["full_name"],
            "phone": data["phone"],
            "people_count": data["people_count"],
            "ages": data["ages"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }).execute()
        return int(response.data[0]["id"])

    async def list_recent_bookings(self, limit: int = 20) -> list[Booking]:
        response = self.client.table("bookings").select(
            "*, tours(title, starts_at)"
        ).in_("status", ["pending", "paid"]).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return [self._map_booking(row) for row in response.data]

    async def get_booking(self, booking_id: int) -> Booking | None:
        response = self.client.table("bookings").select(
            "*, tours(title, starts_at)"
        ).eq("id", booking_id).execute()

        if response.data:
            return self._map_booking(response.data[0])
        return None

    async def list_tour_bookings(self, tour_id: int) -> list[Booking]:
        response = self.client.table("bookings").select(
            "*, tours(title, starts_at)"
        ).eq("tour_id", tour_id).in_(
            "status", ["pending", "paid"]
        ).order("created_at", desc=False).execute()

        return [self._map_booking(row) for row in response.data]

    async def update_booking_status(self, booking_id: int, status: str) -> bool:
        response = self.client.table("bookings").update(
            {"status": status}
        ).eq("id", booking_id).execute()
        return len(response.data) > 0

    async def camping_used_units(self, booking_date: str | None = None) -> dict[str, int]:
        query = self.client.table("camping_bookings").select(
            "item_type, units"
        ).eq("status", "booked")
        if booking_date:
            query = query.eq("booking_date", booking_date)
        response = query.execute()

        result: dict[str, int] = {}
        for row in response.data:
            item_type = row["item_type"]
            result[item_type] = result.get(item_type, 0) + row["units"]
        return result

    async def camping_booked_numbers(self, item_type: str, booking_date: str | None = None) -> set[int]:
        query = self.client.table("camping_bookings").select(
            "item_number"
        ).eq("status", "booked").eq(
            "item_type", item_type
        ).gt("item_number", 0)
        if booking_date:
            query = query.eq("booking_date", booking_date)
        response = query.execute()

        return {int(row["item_number"]) for row in response.data}

    async def create_camping_booking(self, data: dict) -> int:
        response = self.client.table("camping_bookings").insert({
            "user_id": data["user_id"],
            "username": data.get("username"),
            "full_name": data["full_name"],
            "phone": data["phone"],
            "option_code": data["option_code"],
            "option_title": data["option_title"],
            "item_type": data["item_type"],
            "item_number": data["item_number"],
            "units": data["units"],
            "booking_date": data["booking_date"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }).execute()
        return int(response.data[0]["id"])

    async def list_recent_camping_bookings(self, limit: int = 20) -> list[CampingBooking]:
        response = self.client.table("camping_bookings").select(
            "*"
        ).eq("status", "booked").order(
            "created_at", desc=True
        ).limit(limit).execute()

        return [CampingBooking(**row) for row in response.data]

    async def update_camping_booking_status(self, booking_id: int, status: str) -> bool:
        response = self.client.table("camping_bookings").update(
            {"status": status}
        ).eq("id", booking_id).execute()
        return len(response.data) > 0

    async def create_rental_booking(self, data: dict) -> int:
        response = self.client.table("rental_bookings").insert({
            "user_id": data["user_id"],
            "username": data.get("username"),
            "booking_date": data["booking_date"],
            "full_name": data["full_name"],
            "phone": data["phone"],
            "rental_title": data["rental_title"],
            "rental_price": data["rental_price"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }).execute()
        return int(response.data[0]["id"])

    async def list_recent_rental_bookings(self, limit: int = 20) -> list[RentalBooking]:
        response = self.client.table("rental_bookings").select(
            "*"
        ).order("created_at", desc=True).limit(limit).execute()

        return [RentalBooking(**row) for row in response.data]

    async def update_rental_booking_status(self, booking_id: int, status: str) -> bool:
        response = self.client.table("rental_bookings").update(
            {"status": status}
        ).eq("id", booking_id).execute()
        return len(response.data) > 0

    async def reminder_candidates(self) -> list[tuple[Booking, Tour]]:
        response = self.client.table("bookings").select(
            "*, tours(*)"
        ).in_("status", ["pending", "paid"]).eq(
            "tours.is_active", 1
        ).execute()

        result: list[tuple[Booking, Tour]] = []
        for row in response.data:
            booking = self._map_booking(row)
            tour_data = row.get("tours", {})
            if isinstance(tour_data, dict) and tour_data:
                tour = Tour(
                    id=tour_data["id"],
                    title=tour_data["title"],
                    starts_at=tour_data["starts_at"],
                    adult_price=tour_data["adult_price"],
                    child_price=tour_data["child_price"],
                    prepay=tour_data.get("prepay"),
                    seats_total=tour_data["seats_total"],
                    kind=tour_data["kind"],
                    photo_file_id=tour_data.get("photo_file_id"),
                    included=tour_data["included"],
                    route=tour_data["route"],
                    payment_url=tour_data.get("payment_url"),
                    instructor_contact=tour_data.get("instructor_contact"),
                    car_number=tour_data.get("car_number"),
                    is_active=tour_data["is_active"],
                )
                result.append((booking, tour))
        return result

    async def mark_reminder_sent(self, booking_id: int, days_before: int) -> None:
        column = "reminder_3d_sent" if days_before == 3 else "reminder_1d_sent"
        self.client.table("bookings").update(
            {column: 1}
        ).eq("id", booking_id).execute()

    def _map_booking(self, row: dict) -> Booking:
        """Helper to map database row to Booking dataclass"""
        tour_data = row.get("tours", {}) if isinstance(row.get("tours"), dict) else {}

        return Booking(
            id=row["id"],
            tour_id=row["tour_id"],
            user_id=row["user_id"],
            username=row.get("username"),
            full_name=row["full_name"],
            phone=row["phone"],
            people_count=row["people_count"],
            ages=row["ages"],
            status=row["status"],
            created_at=row["created_at"],
            reminder_3d_sent=row.get("reminder_3d_sent", 0),
            reminder_1d_sent=row.get("reminder_1d_sent", 0),
            tour_title=tour_data.get("title") if tour_data else None,
            starts_at=tour_data.get("starts_at") if tour_data else None,
        )
