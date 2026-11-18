
# Dental Clinic Booking Platform

A web application designed to simplify appointment booking and schedule management for a dental clinic.

Patients can book appointments without creating an account, while the clinic manages appointments, patients and availability through a dedicated administrative dashboard.

## How it works

Patients select a dental service and a preferred date. The application calculates available time slots based on the service duration, the doctor's working hours, existing appointments and scheduled breaks.

Booking requests can then be reviewed and managed by the clinic.

## Features

- Online appointment booking without registration
- Automatic time-slot calculation and conflict prevention
- Administrative dashboard for appointment management
- Customizable services, working hours and blocked periods
- Patient database with fuzzy search using RapidFuzz
- Phone number normalization to prevent duplicate records

## Tech Stack

- **Backend:** Python, Django
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite

## Project Status

The application is functional and undergoing further development before deployment.
