"use strict";

// Firebase SDK Imports
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  fetchSignInMethodsForEmail
} from "https://www.gstatic.com/firebasejs/9.22.2/firebase-auth.js";
import {
  getFirestore,
  collection,
  doc,
  query,
  where,
  getDocs
} from "https://www.gstatic.com/firebasejs/9.22.2/firebase-firestore.js";
import {
  getStorage,
  ref,
  uploadBytes,
  getDownloadURL
} from "https://www.gstatic.com/firebasejs/9.22.2/firebase-storage.js";

// Firebase Configuration for Instagram Clone
const firebaseConfig = {
  apiKey: "AIzaSyAMuFRLGz0-kKxwBXu1GmXGKZ7jsmW9ZoQ",
  authDomain: "instagram-assignment.firebaseapp.com",
  projectId: "instagram-assignment",
  storageBucket: "instagram-assignment.appspot.com",
  messagingSenderId: "609279457839",
  appId: "1:609279457839:web:bd55f24c40cdc28b65a4da"
};

// Initialize Firebase App
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const storage = getStorage(app);

// Wait for DOM to load
window.addEventListener("DOMContentLoaded", () => {
  const loginBtn = document.getElementById("login");
  const signupBtn = document.getElementById("signup");
  const signOutBtn = document.getElementById("sign-out");

  // Login Event
  if (loginBtn) {
    loginBtn.addEventListener("click", async () => {
      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;

      try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        const idToken = await user.getIdToken();

        // Set token cookie for backend authentication - set to idToken
        document.cookie = `token=${idToken};path=/;SameSite=Lax`;

        const response = await fetch("/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idToken, email }),
          credentials: "include"
        });

        const data = await response.json();
        if (data.success) {
          window.location.href = "/";
        } else {
          document.getElementById("user-info").textContent = "Login failed: " + (data.error || "Unknown error");
        }
      } catch (error) {
        console.error("Login error:", error);
        document.getElementById("user-info").textContent = "Login failed: " + error.message;
      }
    });
  }

  // Sign-Up Event
  if (signupBtn) {
    signupBtn.addEventListener("click", async () => {
      const name = document.getElementById("name").value.trim();
      const username = document.getElementById("username").value.trim();
      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;
      const profilePicInput = document.getElementById("profilePicInput");
      const errorEl = document.getElementById("user-info");

      errorEl.textContent = "";

      try {
        // Check if username or email already exists via backend
        const checkResponse = await fetch("/check_user_exists", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email }),
          credentials: "include"
        });
        const checkData = await checkResponse.json();
        if (checkData.exists) {
          if (checkData.field === "username") {
            errorEl.textContent = "Username already exists. Please choose another.";
          } else if (checkData.field === "email") {
            errorEl.textContent = "Email already exists. Please use another email.";
          } else {
            errorEl.textContent = "Username or email already exists.";
          }
          return;
        }

        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;

        let profilePicUrl = "/static/images/placeholder.png";

        if (profilePicInput && profilePicInput.files.length > 0) {
          const file = profilePicInput.files[0];
          console.log("Uploading profile image file:", file);
          // Sanitize file name by replacing spaces with underscores
          const sanitizedFileName = file.name.replace(/\s+/g, "_");
          const storageRef = ref(storage, `profile_pictures/${user.uid}/${sanitizedFileName}`);
          try {
            await uploadBytes(storageRef, file);
            profilePicUrl = await getDownloadURL(storageRef);
            console.log("Profile image uploaded, URL:", profilePicUrl);
          } catch (uploadError) {
            console.error("Error uploading profile image:", uploadError);
            throw uploadError;
          }
        }

        // Removed Firestore user document creation here to avoid duplication

        const idToken = await user.getIdToken();

        // Set token cookie for backend authentication - set to idToken
        document.cookie = `token=${idToken};path=/;SameSite=Lax`;

        const response = await fetch("/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ idToken, name, username, email }),
          credentials: "include"
        });

        if (response.ok) {
          window.location.href = "/";
        } else {
          const errorMsg = await response.text();
          errorEl.textContent = "Signup failed: " + errorMsg;
        }
      } catch (error) {
        console.error("Signup error:", error);
        errorEl.textContent = "Signup failed: " + error.message;
      }
    });
  }

  // Sign-Out Event
  if (signOutBtn) {
    signOutBtn.addEventListener("click", async () => {
      try {
        await signOut(auth);
        document.cookie = "token=;path=/;SameSite=Lax";
        window.location.href = "/";
      } catch (error) {
        console.error("Sign-out error:", error);
      }
    });
  }
});
