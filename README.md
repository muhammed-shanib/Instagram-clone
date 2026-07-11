# Instagram Clone

A modern, full-stack Instagram replica developed with **FastAPI** and integrated seamlessly with **Google Firebase Engine**. This platform provides a fully authenticated user experience where users can publish posts, interact with media, discover creators, and manage their social network profiles.

---

##  Features

*   **Secure Authentication:** Integrated token validation utilizing Firebase ID tokens handled cleanly via custom FastAPI middleware dependencies.
*   **Dynamic Feed Generation:** Chronological chronological timeline featuring post aggregation extracted strictly from creators you follow.
*   **Media Hosting Storage:** Interactive post publishing with secure client checks for strictly validated image attachments (`.png`, `.jpg`, `.jpeg`) managed dynamically through Google Cloud Storage.
*   **Interactive Engagement Loop:** REST endpoints built specifically for toggle likes, cascading removals for authored posts, and active comment engagement thresholds.
*   **Social Graphs:** Highly relational follower/following sub-collections tracked down seamlessly inside Cloud Firestore.
*   **Engine Search Optimization:** Native Firestore name-prefix boundary queries execution handling instant user lookups.

---

##  Tech Stack

*   **Backend Framework:** FastAPI (Asynchronous Python)
*   **Database Matrix:** Google Cloud Firestore (NoSQL Architecture)
*   **Object Storage File Server:** Google Cloud Storage
*   **Template Rendering Engine:** Jinja2
*   **Authentication Mechanism:** Google/Firebase OAuth2 Token Infrastructure

---

##  Prerequisites

Before setting things up locally, ensure you have the following installed:
*   Python 3.9+
*   A Google Cloud/Firebase Account

---

##  Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/instagram-clone.git](https://github.com/YOUR_USERNAME/instagram-clone.git)
   cd instagram-clone

## Environment Isolation & Dependencies Configuration:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

## Configure Firebase Service Account Credentials:

Download your private Service Account key json folder out of the Firebase Console.

Save it locally as firebase-credentials.json (Ensure this file remains listed inside your .gitignore).

Export your global runtime environmental pointer pointing to the path location of the configuration file:

Project Structure

├── static/              # CSS Stylesheets, Clientside JS Scripts, Placeholders
├── templates/           # Jinja2 HTML views (home, login, profile, post etc.)
├── main.py              # Central application core routing & middleware controls
├── requirements.txt     # Python production libraries matrix
└── .gitignore           # Ignored source paths tracking prevention control
