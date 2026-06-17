from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import aiosqlite


@dataclass
class Tour:
    id: int
    title: str
    starts_at: str
    price: int
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
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tours (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    prepay INTEGER,
                    seats_total INTEGER NOT NULL DEFAULT 0,
                    kind TEXT NOT NULL,
                    photo_file_id TEXT,
                    included TEXT NOT NULL,
                    route TEXT NOT NULL,
                    payment_url TEXT,
                    instructor_contact TEXT,
                    car_number TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_column(
                db,
                table="tours",
                column="seats_total",
                definition="INTEGER NOT NULL DEFAULT 0",
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tour_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    people_count INTEGER NOT NULL,
                    ages TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    reminder_3d_sent INTEGER NOT NULL DEFAULT 0,
                    reminder_1d_sent INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(tour_id) REFERENCES tours(id)
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS camping_bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    option_code TEXT NOT NULL,
                    option_title TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    item_number INTEGER NOT NULL DEFAULT 0,
                    units INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'booked',
                    booking_date TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS rental_bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    booking_date TEXT,
                    phone TEXT NOT NULL,
                    rental_title TEXT NOT NULL,
                    rental_price INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_column(
                db,
                table="camping_bookings",
                column="item_number",
                definition="INTEGER NOT NULL DEFAULT 0",
            )
            await self._ensure_column(
                db,
                table="camping_bookings",
                column="booking_date",
                definition="TEXT",
            )
            await self._ensure_column(
                db,
                table="rental_bookings",
                column="booking_date",
                definition="TEXT",
            )
            await db.commit()

    async def create_rental_booking(self, data: dict) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO rental_bookings (
                    user_id,
                    username,
                    booking_date,
                    full_name,
                    phone,
                    rental_title,
                    rental_price,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["user_id"],
                    data.get("username"),
                    data["booking_date"],
                    data["full_name"],
                    data["phone"],
                    data["rental_title"],
                    data["rental_price"],
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)
    
    async def list_recent_rental_bookings(
        self,
        limit: int = 20
    ) -> list[RentalBooking]:

        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT *
                FROM rental_bookings
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )

            rows = await cursor.fetchall()

            return [
                RentalBooking(**dict(row))
                for row in rows
            ]

    async def update_rental_booking_status(
        self,
        booking_id: int,
        status: str
    ) -> bool:

        async with aiosqlite.connect(self.path) as db:

            cursor = await db.execute(
                """
                UPDATE rental_bookings
                SET status = ?
                WHERE id = ?
                """,
                (status, booking_id)
            )

            await db.commit()

            return cursor.rowcount > 0

    async def _ensure_column(
        self,
        db: aiosqlite.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in await cursor.fetchall()}
        if column not in columns:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    async def create_tour(self, data: dict) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO tours (
                    title, starts_at, price, prepay, seats_total, kind, photo_file_id, included,
                    route, payment_url, instructor_contact, car_number, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["title"],
                    data["starts_at"],
                    data["price"],
                    data.get("prepay"),
                    data["seats_total"],
                    data["kind"],
                    data.get("photo_file_id"),
                    data["included"],
                    data["route"],
                    data.get("payment_url"),
                    data.get("instructor_contact"),
                    data.get("car_number"),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_active_tours(self) -> list[Tour]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tours WHERE is_active = 1 ORDER BY starts_at ASC"
            )
            rows = await cursor.fetchall()
            return [Tour(**dict(row)) for row in rows]

    async def list_inactive_tours(self) -> list[Tour]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tours WHERE is_active = 0 ORDER BY starts_at DESC"
            )
            rows = await cursor.fetchall()
            return [Tour(**dict(row)) for row in rows]

    async def get_tour(self, tour_id: int) -> Tour | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM tours WHERE id = ?", (tour_id,))
            row = await cursor.fetchone()
            return Tour(**dict(row)) if row else None

    async def deactivate_tour(self, tour_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "UPDATE tours SET is_active = 0 WHERE id = ?",
                (tour_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def activate_tour(self, tour_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "UPDATE tours SET is_active = 1 WHERE id = ?",
                (tour_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def create_booking(self, data: dict) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO bookings (
                    tour_id, user_id, username, full_name, phone,
                    people_count, ages, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["tour_id"],
                    data["user_id"],
                    data.get("username"),
                    data["full_name"],
                    data["phone"],
                    data["people_count"],
                    data["ages"],
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_recent_bookings(self, limit: int = 20) -> list[Booking]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT b.*, t.title AS tour_title, t.starts_at AS starts_at
                FROM bookings b
                JOIN tours t ON t.id = b.tour_id
                WHERE b.status IN ('pending', 'paid')
                ORDER BY b.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [Booking(**dict(row)) for row in rows]

    async def get_booking(self, booking_id: int) -> Booking | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT b.*, t.title AS tour_title, t.starts_at AS starts_at
                FROM bookings b
                JOIN tours t ON t.id = b.tour_id
                WHERE b.id = ?
                """,
                (booking_id,),
            )
            row = await cursor.fetchone()
            return Booking(**dict(row)) if row else None

    async def list_tour_bookings(self, tour_id: int) -> list[Booking]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT b.*, t.title AS tour_title, t.starts_at AS starts_at
                FROM bookings b
                JOIN tours t ON t.id = b.tour_id
                WHERE b.tour_id = ? AND b.status IN ('pending', 'paid')
                ORDER BY b.created_at ASC
                """,
                (tour_id,),
            )
            rows = await cursor.fetchall()
            return [Booking(**dict(row)) for row in rows]

    async def update_booking_status(self, booking_id: int, status: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "UPDATE bookings SET status = ? WHERE id = ?",
                (status, booking_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def camping_used_units(self) -> dict[str, int]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                SELECT item_type, COALESCE(SUM(units), 0) AS used
                FROM camping_bookings
                WHERE status = 'booked'
                GROUP BY item_type
                """
            )
            rows = await cursor.fetchall()
            return {row[0]: int(row[1]) for row in rows}

    async def camping_booked_numbers(self, item_type: str) -> set[int]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                SELECT item_number
                FROM camping_bookings
                WHERE status = 'booked'
                    AND item_type = ?
                    AND item_number > 0
                """,
                (item_type,),
            )
            rows = await cursor.fetchall()
            return {int(row[0]) for row in rows}

    async def create_camping_booking(self, data: dict) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO camping_bookings (
                    user_id, username, full_name, phone, option_code,
                    option_title, item_type, item_number, units,booking_date, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["user_id"],
                    data.get("username"),
                    data["full_name"],
                    data["phone"],
                    data["option_code"],
                    data["option_title"],
                    data["item_type"],
                    data["item_number"],
                    data["units"],
                    data["booking_date"],
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_recent_camping_bookings(self, limit: int = 20) -> list[CampingBooking]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM camping_bookings
                WHERE status = 'booked'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [CampingBooking(**dict(row)) for row in rows]

    async def update_camping_booking_status(self, booking_id: int, status: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "UPDATE camping_bookings SET status = ? WHERE id = ?",
                (status, booking_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def reminder_candidates(self) -> list[tuple[Booking, Tour]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT
                    b.id AS b_id, b.tour_id, b.user_id, b.username, b.full_name,
                    b.phone, b.people_count, b.ages, b.status, b.created_at,
                    b.reminder_3d_sent, b.reminder_1d_sent,
                    t.id AS t_id, t.title, t.starts_at, t.price, t.prepay,
                    t.seats_total, t.kind,
                    t.photo_file_id, t.included, t.route, t.payment_url,
                    t.instructor_contact, t.car_number, t.is_active
                FROM bookings b
                JOIN tours t ON t.id = b.tour_id
                WHERE b.status IN ('pending', 'paid') AND t.is_active = 1
                """
            )
            rows = await cursor.fetchall()

        result: list[tuple[Booking, Tour]] = []
        for row in rows:
            booking = Booking(
                id=row["b_id"],
                tour_id=row["tour_id"],
                user_id=row["user_id"],
                username=row["username"],
                full_name=row["full_name"],
                phone=row["phone"],
                people_count=row["people_count"],
                ages=row["ages"],
                status=row["status"],
                created_at=row["created_at"],
                reminder_3d_sent=row["reminder_3d_sent"],
                reminder_1d_sent=row["reminder_1d_sent"],
                tour_title=row["title"],
                starts_at=row["starts_at"],
            )
            tour = Tour(
                id=row["t_id"],
                title=row["title"],
                starts_at=row["starts_at"],
                price=row["price"],
                prepay=row["prepay"],
                seats_total=row["seats_total"],
                kind=row["kind"],
                photo_file_id=row["photo_file_id"],
                included=row["included"],
                route=row["route"],
                payment_url=row["payment_url"],
                instructor_contact=row["instructor_contact"],
                car_number=row["car_number"],
                is_active=row["is_active"],
            )
            result.append((booking, tour))
        return result

    async def mark_reminder_sent(self, booking_id: int, days_before: int) -> None:
        column = "reminder_3d_sent" if days_before == 3 else "reminder_1d_sent"
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE bookings SET {column} = 1 WHERE id = ?",
                (booking_id,),
            )
            await db.commit()

