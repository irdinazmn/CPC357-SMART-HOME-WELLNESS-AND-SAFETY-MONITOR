# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore, auth
import streamlit as st
import requests
import json
import os
import random
from datetime import datetime, timedelta

class FirebaseConfig:
    # FIREBASE CONFIG
    WEB_CONFIG = {
        "apiKey": "AIzaSyC9BJnfNySJBMy3WJfZgw9csFwhUgDrDco",
        "authDomain": "smarthome-5b4f0.firebaseapp.com",
        "projectId": "smarthome-5b4f0",
        "storageBucket": "smarthome-5b4f0.firebasestorage.app",
        "messagingSenderId": "738770707243",
        "appId": "1:738770707243:web:9d33256707bcd05b40db6e",
        "measurementId": "G-CYW2PMVEC7"
    }
    
    API_KEY = WEB_CONFIG["apiKey"] 

class FirebaseAuth:
    def __init__(self, api_key=None):
        self.api_key = api_key or FirebaseConfig.API_KEY
        self.base_url = "https://identitytoolkit.googleapis.com/v1"
    
    def sign_in(self, email, password):
        """Sign in with email/password using REST API"""
        url = f"{self.base_url}/accounts:signInWithPassword?key={self.api_key}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Store tokens in session
            st.session_state.id_token = data.get('idToken')
            st.session_state.refresh_token = data.get('refreshToken')
            st.session_state.user_id = data.get('localId')
            st.session_state.user_email = data.get('email')

            return data
        except requests.exceptions.RequestException as e:
            error_msg = "Network error. Check internet connection."
            if hasattr(e.response, 'json'):
                error_data = e.response.json()
                error_msg = error_data.get('error', {}).get('message', str(e))
            raise Exception(f"Login failed: {error_msg}")
    
    def sign_up(self, email, password, display_name=""):
        """Create new user account"""
        url = f"{self.base_url}/accounts:signUp?key={self.api_key}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        if display_name:
            payload["displayName"] = display_name

        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            raise Exception(f"Signup failed: {error_data.get('error', {}).get('message', 'Unknown error')}")
    
    def get_user_info(self, id_token):
        """Get user info from ID token"""
        url = f"{self.base_url}/accounts:lookup?key={self.api_key}"

        payload = {"idToken": id_token}
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            return users[0] if users else None
        return None
    
    def verify_token(self, id_token):
        """Verify ID token"""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={self.api_key}"

        payload = {"idToken": id_token}
        response = requests.post(url, json=payload)

        return response.status_code == 200
    
    def send_password_reset(self, email):
        """Send password reset email"""
        url = f"{self.base_url}/accounts:sendOobCode?key={self.api_key}"

        payload = {
            "requestType": "PASSWORD_RESET",
            "email": email
        }

        response = requests.post(url, json=payload)
        return response.status_code == 200

class FirebaseAdmin:
    _instance = None
    
    def __init__(self, service_account_key_path="firebase-key.json"):
        if FirebaseAdmin._instance is not None:
            return

        # Initialize Admin SDK
        if not os.path.exists(service_account_key_path):
            raise FileNotFoundError(f"Key not found: {service_account_key_path}")

        self.cred = credentials.Certificate(service_account_key_path)
        if not firebase_admin._apps:
            self.app = firebase_admin.initialize_app(self.cred)
        else:
            self.app = firebase_admin.get_app()

        self.db = firestore.client()

        self.web_api_key = "AIzaSyBqFJrE2CWTN9fcLVk4TQ4usFfhbg3xv2c" 
        FirebaseAdmin._instance = self
    
    @staticmethod
    def get_instance():
        if FirebaseAdmin._instance is None:
            FirebaseAdmin()
        return FirebaseAdmin._instance

        return code
