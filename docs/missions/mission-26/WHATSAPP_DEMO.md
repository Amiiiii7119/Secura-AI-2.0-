# WhatsApp Simulation Demo Guide

## 1. Features
- **Ephemeral OTP Login:** Clean modal prompting for Indian mobile number (`+91 ...`). Generates a 6-digit code with developer test badge for instant autofill.
- **Chats & Supergroups:** Side-by-side split screen showing active conversations (Priya, Cyber Cell, Delhi Alerts).
- **Read Receipts:** Double-check status progression (`sent` -> `delivered` -> `read`).
- **Pre-Send Interception:** Attached media is evaluated before sending; blocked synthetic files are prevented from entering the chat stream.

## 2. Walkthrough Steps
1. Select the **WhatsApp** tab on the navigation bar.
2. Authenticate using the ephemeral OTP flow with demo credentials.
3. Open a direct chat with **Priya** and send a text message.
4. Note the instant blue double-check icon confirming delivery.
5. Click **New Group**, name it "Emergency Taskforce", and add members.