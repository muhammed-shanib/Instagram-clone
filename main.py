import os
import uuid
from fastapi import FastAPI, Request, Response, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import http_exception_handler
from fastapi.requests import Request as FastAPIRequest
from fastapi.responses import RedirectResponse as FastAPIRedirectResponse

import google.auth.transport.requests
import google.oauth2.id_token

from google.cloud import firestore
from google.cloud import storage

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: FastAPIRequest, exc: HTTPException):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return FastAPIRedirectResponse(url="/login")
    return await http_exception_handler(request, exc)

# Initialize Firestore client
db = firestore.Client()

# Initialize Firebase Storage client
storage_client = storage.Client()
bucket_name = "instagram-assignment.appspot.com"
bucket = storage_client.bucket(bucket_name)

# Token verification using google.oauth2.id_token.verify_firebase_token
from fastapi.responses import RedirectResponse
from fastapi.requests import Request as FastAPIRequest

from fastapi import HTTPException

async def verify_token(request: FastAPIRequest):
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization token")

    request_adapter = google.auth.transport.requests.Request()
    try:
        decoded_token = google.oauth2.id_token.verify_firebase_token(token, request_adapter)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    uid = decoded_token.get("uid") or decoded_token.get("user_id")
    email = decoded_token.get("email")
    if not uid or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or user not found")

    # Check if user document exists in Firestore by UID
    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {"uid": uid, "email": email}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/login")
async def login_user(request: Request):
    data = await request.json()
    token = data.get("idToken")

    if not token:
        return JSONResponse(content={"success": False, "error": "Missing fields"}, status_code=400)

    # Verify token and extract uid
    request_adapter = google.auth.transport.requests.Request()
    try:
        decoded_token = google.oauth2.id_token.verify_firebase_token(token, request_adapter)
    except Exception:
        return JSONResponse(content={"success": False, "error": "Invalid token"}, status_code=401)

    uid = decoded_token.get("uid") or decoded_token.get("user_id")
    if not uid:
        return JSONResponse(content={"success": False, "error": "Invalid token data"}, status_code=401)

    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if user_doc.exists:
        response = JSONResponse(content={"success": True, "username": user_doc.to_dict().get("username")})
        return response
    else:
        return JSONResponse(content={"success": False, "error": "Invalid token or user not found"}, status_code=401)

@app.post("/signup")
async def signup_user(request: Request):
    data = await request.json()
    token = data.get("idToken")
    name = data.get("name")
    username = data.get("username")
    email = data.get("email")

    if not token or not name or not username or not email:
        return JSONResponse(content={"success": False, "error": "Missing fields"}, status_code=400)

    profile_pic_url = ""

    # Verify token and extract uid
    request_adapter = google.auth.transport.requests.Request()
    try:
        decoded_token = google.oauth2.id_token.verify_firebase_token(token, request_adapter)
    except Exception:
        return JSONResponse(content={"success": False, "error": "Invalid token"}, status_code=401)

    uid = decoded_token.get("uid") or decoded_token.get("user_id")
    if not uid:
        return JSONResponse(content={"success": False, "error": "Invalid token data"}, status_code=401)

    # Check if username or email already exists in Firestore
    users_ref = db.collection("User")
    try:
        username_query = users_ref.where("username", "==", username).limit(1).stream()
        for doc in username_query:
            return JSONResponse(content={"success": False, "error": "Username already exists"}, status_code=400)

        email_query = users_ref.where("email", "==", email).limit(1).stream()
        for doc in email_query:
            return JSONResponse(content={"success": False, "error": "Email already exists"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": f"Permission error: {str(e)}"}, status_code=403)

    user_ref = db.collection("User").document(uid)
    user_ref.set({
        "name": name,
        "username": username,
        "email": email,
        "profile_pic_url": profile_pic_url,
        "bio": ""
    })

    # Create empty followers and following subcollections with a placeholder document
    followers_ref = user_ref.collection("followers")
    following_ref = user_ref.collection("following")

    # Remove placeholder documents from followers and following subcollections if they exist
    followers_ref.document("_init").delete()
    following_ref.document("_init").delete()

    response = JSONResponse(content={"success": True, "username": username})
    return response

@app.post("/check_user_exists")
async def check_user_exists(request: Request):
    data = await request.json()
    username = data.get("username")
    email = data.get("email")

    if not username or not email:
        return JSONResponse(content={"success": False, "error": "Missing username or email"}, status_code=400)

    users_ref = db.collection("User")

    username_query = users_ref.where("username", "==", username).limit(1).stream()
    for doc in username_query:
        return JSONResponse(content={"exists": True, "field": "username"}, status_code=200)

    email_query = users_ref.where("email", "==", email).limit(1).stream()
    for doc in email_query:
        return JSONResponse(content={"exists": True, "field": "email"}, status_code=200)

    return JSONResponse(content={"exists": False}, status_code=200)
    data = await request.json()
    token = data.get("idToken")
    name = data.get("name")
    username = data.get("username")
    email = data.get("email")

    if not token or not name or not username or not email:
        return JSONResponse(content={"success": False, "error": "Missing fields"}, status_code=400)

    profile_pic_url = ""

    # Verify token and extract uid
    request_adapter = google.auth.transport.requests.Request()
    try:
        decoded_token = google.oauth2.id_token.verify_firebase_token(token, request_adapter)
    except Exception:
        return JSONResponse(content={"success": False, "error": "Invalid token"}, status_code=401)

    uid = decoded_token.get("uid") or decoded_token.get("user_id")
    if not uid:
        return JSONResponse(content={"success": False, "error": "Invalid token data"}, status_code=401)

    # Check if username or email already exists in Firestore
    users_ref = db.collection("User")
    try:
        username_query = users_ref.where("username", "==", username).limit(1).stream()
        for doc in username_query:
            return JSONResponse(content={"success": False, "error": "Username already exists"}, status_code=400)

        email_query = users_ref.where("email", "==", email).limit(1).stream()
        for doc in email_query:
            return JSONResponse(content={"success": False, "error": "Email already exists"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": f"Permission error: {str(e)}"}, status_code=403)

    user_ref = db.collection("User").document(uid)
    user_ref.set({
        "name": name,
        "username": username,
        "email": email,
        "profile_pic_url": profile_pic_url,
        "bio": ""
    })

    # Create empty followers and following subcollections with a placeholder document
    followers_ref = user_ref.collection("followers")
    following_ref = user_ref.collection("following")

    # Remove placeholder documents from followers and following subcollections if they exist
    followers_ref.document("_init").delete()
    following_ref.document("_init").delete()

    response = JSONResponse(content={"success": True, "username": username})
    return response

@app.get("/api/profile")
async def get_profile(decoded_token=Depends(verify_token)):
    uid = decoded_token.get("uid")
    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return JSONResponse(content={"success": False, "error": "User not found"}, status_code=404)
    user = user_doc.to_dict()
    return JSONResponse(content={
        "success": True,
        "username": user.get("username"),
        "name": user.get("name"),
        "bio": user.get("bio", "")
    })

from fastapi.responses import RedirectResponse

@app.get("/followers.html", response_class=HTMLResponse)
async def followers_page(request: Request, user: str, type: str = "followers", decoded_token=Depends(verify_token)):
    # Validate user exists
    users_ref = db.collection("User")
    query = users_ref.where("username", "==", user).limit(1).stream()
    user_doc = None
    user_ref = None
    for doc in query:
        user_doc = doc
        user_ref = users_ref.document(doc.id)
        break
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    # Get logged-in user's username
    current_username = ""
    current_user_ref = db.collection("User").document(decoded_token.get("uid"))
    current_user_doc = current_user_ref.get()
    if current_user_doc.exists:
        current_username = current_user_doc.to_dict().get("username", "")

    if type == "following":
        # Fetch following list ordered by followedAt descending
        following_ref = user_ref.collection("following").order_by("followedAt", direction=firestore.Query.DESCENDING)
        following_docs = following_ref.stream()
        following = []
        for doc in following_docs:
            following_uid = doc.id
            following_doc = users_ref.document(following_uid).get()
            if following_doc.exists:
                followee = following_doc.to_dict()
                following.append({
                    "username": followee.get("username", ""),
                    "name": followee.get("name", ""),
                    "profile_pic_url": followee.get("profile_pic_url", ""),
                    "is_following": False  # will update below
                })

        # Determine if current user is following each followee
        current_uid = decoded_token.get("uid")
        current_user_ref = users_ref.document(current_uid)
        current_following_ref = current_user_ref.collection("following")
        current_following_docs = list(current_following_ref.stream())
        current_following_uids = {doc.id for doc in current_following_docs}

        for followee in following:
            followee_username = followee["username"]
            # Find followee's UID by username
            followee_query = users_ref.where("username", "==", followee_username).limit(1).stream()
            followee_uid = None
            for doc in followee_query:
                followee_uid = doc.id
                break
            followee["is_following"] = followee_uid in current_following_uids

        return templates.TemplateResponse("followers.html", {
            "request": request,
            "username": user,
            "current_user_username": current_username,
            "followers": following
        })
    else:
        # Fetch followers list ordered by followedAt descending
        followers_ref = user_ref.collection("followers").order_by("followedAt", direction=firestore.Query.DESCENDING)
        followers_docs = followers_ref.stream()
        followers = []
        for doc in followers_docs:
            follower_uid = doc.id
            follower_doc = users_ref.document(follower_uid).get()
            if follower_doc.exists:
                follower = follower_doc.to_dict()
                followers.append({
                    "username": follower.get("username", ""),
                    "name": follower.get("name", ""),
                    "profile_pic_url": follower.get("profile_pic_url", ""),
                    "is_following": False  # will update below
                })

        # Determine if current user is following each follower
        current_uid = decoded_token.get("uid")
        current_user_ref = users_ref.document(current_uid)
        current_following_ref = current_user_ref.collection("following")
        current_following_docs = list(current_following_ref.stream())
        current_following_uids = {doc.id for doc in current_following_docs}

        for follower in followers:
            follower_username = follower["username"]
            # Find follower's UID by username
            follower_query = users_ref.where("username", "==", follower_username).limit(1).stream()
            follower_uid = None
            for doc in follower_query:
                follower_uid = doc.id
                break
            follower["is_following"] = follower_uid in current_following_uids

        return templates.TemplateResponse("followers.html", {
            "request": request,
            "username": user,
            "current_user_username": current_username,
            "followers": followers
        })

@app.get("/following.html", response_class=HTMLResponse)
async def following_page(request: Request, user: str, decoded_token=Depends(verify_token)):
    # Validate user exists
    users_ref = db.collection("User")
    query = users_ref.where("username", "==", user).limit(1).stream()
    user_doc = None
    user_ref = None
    for doc in query:
        user_doc = doc
        user_ref = users_ref.document(doc.id)
        break
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    # Get logged-in user's username
    current_username = ""
    current_user_ref = db.collection("User").document(decoded_token.get("uid"))
    current_user_doc = current_user_ref.get()
    if current_user_doc.exists:
        current_username = current_user_doc.to_dict().get("username", "")

    # Fetch following list
    following_ref = user_ref.collection("following")
    following_docs = following_ref.stream()
    following = []
    for doc in following_docs:
        following_uid = doc.id
        following_doc = users_ref.document(following_uid).get()
        if following_doc.exists:
            followee = following_doc.to_dict()
            following.append({
                "username": followee.get("username", ""),
                "name": followee.get("name", ""),
                "profile_pic_url": followee.get("profile_pic_url", ""),
                "is_following": False  # will update below
            })

    # Determine if current user is following each followee
    current_uid = decoded_token.get("uid")
    current_user_ref = users_ref.document(current_uid)
    current_following_ref = current_user_ref.collection("following")
    current_following_docs = list(current_following_ref.stream())
    current_following_uids = {doc.id for doc in current_following_docs}

    for followee in following:
        followee_username = followee["username"]
        # Find followee's UID by username
        followee_query = users_ref.where("username", "==", followee_username).limit(1).stream()
        followee_uid = None
        for doc in followee_query:
            followee_uid = doc.id
            break
        followee["is_following"] = followee_uid in current_following_uids

    return templates.TemplateResponse("following.html", {
        "request": request,
        "username": user,
        "current_user_username": current_username,
        "following": following
    })

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, decoded_token=Depends(verify_token)):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/api/search_users")
async def search_users(q: str, decoded_token=Depends(verify_token)):
    # Search users by name prefix
    users_ref = db.collection("User")
    query = users_ref.order_by("name").start_at([q]).end_at([q + "\uf8ff"]).limit(20)
    results = query.stream()
    users = []
    for doc in results:
        user = doc.to_dict()
        users.append({
            "username": user.get("username", ""),
            "name": user.get("name", ""),
            "profile_pic_url": user.get("profile_pic_url", "")
        })
    return JSONResponse(content={"success": True, "users": users})

@app.get("/api/users/{username}/followers")
async def get_followers(username: str, decoded_token=Depends(verify_token)):
    users_ref = db.collection("User")
    query = users_ref.where("username", "==", username).limit(1).stream()
    user_doc = None
    user_ref = None
    for doc in query:
        user_doc = doc
        user_ref = users_ref.document(doc.id)
        break
    if not user_doc:
        return JSONResponse(content={"success": False, "error": "User not found"}, status_code=404)

    followers_ref = user_ref.collection("followers")
    followers_docs = followers_ref.stream()
    followers = []
    for doc in followers_docs:
        follower_uid = doc.id
        follower_doc = users_ref.document(follower_uid).get()
        if follower_doc.exists:
            follower = follower_doc.to_dict()
            followers.append({
                "username": follower.get("username", ""),
                "name": follower.get("name", ""),
                "profile_pic_url": follower.get("profile_pic_url", ""),
                "is_following": False  # will update below
            })

    # Determine if current user is following each follower
    current_uid = decoded_token.get("uid")
    current_user_ref = users_ref.document(current_uid)
    current_following_ref = current_user_ref.collection("following")
    current_following_docs = list(current_following_ref.stream())
    current_following_uids = {doc.id for doc in current_following_docs}

    for follower in followers:
        follower_username = follower["username"]
        # Find follower's UID by username
        follower_query = users_ref.where("username", "==", follower_username).limit(1).stream()
        follower_uid = None
        for doc in follower_query:
            follower_uid = doc.id
            break
        follower["is_following"] = follower_uid in current_following_uids

    return JSONResponse(content={"success": True, "followers": followers})

@app.get("/api/users/{username}/following")
async def get_following(username: str, decoded_token=Depends(verify_token)):
    users_ref = db.collection("User")
    query = users_ref.where("username", "==", username).limit(1).stream()
    user_doc = None
    user_ref = None
    for doc in query:
        user_doc = doc
        user_ref = users_ref.document(doc.id)
        break
    if not user_doc:
        return JSONResponse(content={"success": False, "error": "User not found"}, status_code=404)

    following_ref = user_ref.collection("following")
    following_docs = following_ref.stream()
    following = []
    for doc in following_docs:
        following_uid = doc.id
        following_doc = users_ref.document(following_uid).get()
        if following_doc.exists:
            followee = following_doc.to_dict()
            following.append({
                "username": followee.get("username", ""),
                "name": followee.get("name", ""),
                "profile_pic_url": followee.get("profile_pic_url", ""),
                "is_following": False  # will update below
            })

    # Determine if current user is following each followee
    current_uid = decoded_token.get("uid")
    current_user_ref = users_ref.document(current_uid)
    current_following_ref = current_user_ref.collection("following")
    current_following_docs = list(current_following_ref.stream())
    current_following_uids = {doc.id for doc in current_following_docs}

    for followee in following:
        followee_username = followee["username"]
        # Find followee's UID by username
        followee_query = users_ref.where("username", "==", followee_username).limit(1).stream()
        followee_uid = None
        for doc in followee_query:
            followee_uid = doc.id
            break
        followee["is_following"] = followee_uid in current_following_uids

    return JSONResponse(content={"success": True, "following": following})

from fastapi import Form

@app.post("/deletepost")
async def delete_post(post_id: str = Form(...), decoded_token=Depends(verify_token)):
    if not post_id:
        return JSONResponse({"success": False, "error": "Post ID is required"}, status_code=400)

    uid = decoded_token.get("uid")
    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return JSONResponse({"success": False, "error": "User not found"}, status_code=404)
    user = user_doc.to_dict()
    username = user.get("username")

    post_ref = db.collection("Post").document(post_id)
    post_doc = post_ref.get()
    if not post_doc.exists:
        return JSONResponse({"success": False, "error": "Post not found"}, status_code=404)

    post = post_doc.to_dict()
    if post.get("Username") != username:
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=403)

    # Delete likes subcollection
    likes_ref = post_ref.collection("likes")
    likes_docs = list(likes_ref.stream())
    for doc in likes_docs:
        doc.reference.delete()

    # Delete comments subcollection
    comments_ref = post_ref.collection("comments")
    comments_docs = list(comments_ref.stream())
    for doc in comments_docs:
        doc.reference.delete()

    # Delete the post document
    post_ref.delete()

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/profile", status_code=303)

@app.post("/editpost")
async def edit_post(request: Request, decoded_token=Depends(verify_token)):
    data = await request.json()
    post_id = data.get("post_id")
    new_caption = data.get("caption", "").strip()
    if not post_id or new_caption is None:
        return JSONResponse({"success": False, "error": "Post ID and caption are required"}, status_code=400)

    uid = decoded_token.get("uid")
    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return JSONResponse({"success": False, "error": "User not found"}, status_code=404)
    user = user_doc.to_dict()
    username = user.get("username")

    post_ref = db.collection("Post").document(post_id)
    post_doc = post_ref.get()
    if not post_doc.exists:
        return JSONResponse({"success": False, "error": "Post not found"}, status_code=404)

    post = post_doc.to_dict()
    if post.get("Username") != username:
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=403)

    post_ref.update({"caption": new_caption})
    return JSONResponse({"success": True})

@app.get("/user/{username}", response_class=HTMLResponse)
async def user_profile(username: str, request: Request, decoded_token=Depends(verify_token)):
    current_email = decoded_token.get("email")
    users_ref = db.collection("User")
    query = users_ref.where("username", "==", username).limit(1)
    results = query.stream()
    user_doc = None
    user_ref = None
    for doc in results:
        user_doc = doc
        user_ref = users_ref.document(doc.id)
        break
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_doc.to_dict()

    # Fetch posts by user using Username instead of userId
    posts_ref = db.collection("Post")
    query_posts = posts_ref.where("Username", "==", username).order_by("Date", direction=firestore.Query.DESCENDING)
    posts_docs = query_posts.stream()
    posts = []
    for doc in posts_docs:
        post = doc.to_dict()
        post['postId'] = doc.id
        posts.append(post)

    followers_ref = user_ref.collection("followers")
    following_ref = user_ref.collection("following")

    followers_count = len(list(followers_ref.stream()))
    following_count = len(list(following_ref.stream()))

    is_following = False
    current_username = ""
    current_user_ref = db.collection("User").document(decoded_token.get("uid"))
    current_user_doc = current_user_ref.get()
    if current_user_doc.exists:
        current_username = current_user_doc.to_dict().get("username", "")
    is_own_profile = (user.get("username") == current_username)

    # Check if current user is following this user
    if current_email:
        # Find current user's UID from decoded_token
        current_uid = decoded_token.get("uid")
        if current_uid:
            follower_doc = followers_ref.document(current_uid).get()
            is_following = follower_doc.exists

    # Get logged-in user's username to pass to template for currentUsername in JS
    current_user_ref = db.collection("User").document(decoded_token.get("uid"))
    current_user_doc = current_user_ref.get()
    current_user_username = ""
    if current_user_doc.exists:
        current_user_username = current_user_doc.to_dict().get("username", "")

    return templates.TemplateResponse("searched_user.html", {
        "request": request,
        "username": user.get("username", ""),
        "full_name": user.get("name", ""),
        "bio": user.get("bio", ""),
        "profile_pic_url": user.get("profile_pic_url", ""),
        "posts": posts,
        "posts_count": len(posts),
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following,
        "is_own_profile": is_own_profile,
        "current_user_username": current_user_username
    })

@app.post("/editprofile")
async def edit_profile(
    request: Request,
    username: str = Form(...),
    fullName: str = Form(...),
    bio: str = Form(""),
    remove_profile_image: str = Form("false"),
    profile_image: UploadFile = File(None),
    decoded_token=Depends(verify_token)
):
    uid = decoded_token.get("uid")
    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_doc.to_dict()
    old_username = user.get("username", "")

    # Check if new username already exists and is not the current user's username
    if username != old_username:
        users_ref = db.collection("User")
        username_query = users_ref.where("username", "==", username).limit(1).stream()
        for doc in username_query:
            # Username already taken by another user
            error_message = "Username already taken."
            return templates.TemplateResponse("editprofile.html", {
                "request": request,
                "username": user.get("username", ""),
                "full_name": user.get("name", ""),
                "bio": user.get("bio", ""),
                "profile_pic_url": user.get("profile_pic_url", "/static/images/placeholder.png"),
                "error_message": error_message
            })

    if remove_profile_image == "true":
        # Remove profile picture URL from user document
        user["profile_pic_url"] = ""
        # Optionally delete the existing profile picture from Firebase Storage
        # If you want to delete the old image from storage, you can implement it here
        # For now, we just remove the URL from Firestore
    elif profile_image and profile_image.filename != "":
        try:
            ext = os.path.splitext(profile_image.filename)[1]
            unique_filename = f"{uuid.uuid4()}{ext}"
            blob = bucket.blob(f"profile_pictures/{unique_filename}")
            blob.upload_from_file(profile_image.file, content_type=profile_image.content_type)
            # Make the blob publicly accessible
            blob.make_public()
            profile_pic_url = blob.public_url
            user["profile_pic_url"] = profile_pic_url
            print(f"Profile image uploaded successfully: {profile_pic_url}")
        except Exception as e:
            print(f"Error uploading profile image: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload profile image")

    user["username"] = username
    user["name"] = fullName
    user["bio"] = bio

    # Update Firestore document
    user_ref.update({
        "username": username,
        "name": fullName,
        "bio": bio,
        "profile_pic_url": user.get("profile_pic_url")
    })

    # Update username in all posts made by this user
    try:
        posts_ref = db.collection("Post")
        query_posts = posts_ref.where("Username", "==", old_username).stream()
        count_posts = 0
        for post_doc in query_posts:
            post_ref = post_doc.reference
            post_ref.update({"Username": username})
            count_posts += 1
        print(f"Updated username in {count_posts} posts for user {old_username}")
    except Exception as e:
        print(f"Error updating username in posts: {e}")

    # Update profilePicUrl in all comments made by this user
    try:
        comments_query = db.collection_group("comments").stream()
        count = 0
        total = 0
        for comment_doc in comments_query:
            total += 1
            comment_data = comment_doc.to_dict()
            comment_username = comment_data.get("username", "")
            if comment_username.lower() == username.lower():
                comment_ref = comment_doc.reference
                current_profile_pic_url = comment_doc.to_dict().get("profilePicUrl", "")
                new_profile_pic_url = user.get("profile_pic_url", "")
                if current_profile_pic_url != new_profile_pic_url:
                    comment_ref.update({"profilePicUrl": new_profile_pic_url})
                    count += 1
        print(f"Checked {total} comments, updated profilePicUrl in {count} comments for user {username}")
    except Exception as e:
        print(f"Error updating profilePicUrl in comments: {e}")

    return RedirectResponse(url="/profile", status_code=303)

@app.get("/editprofile", response_class=HTMLResponse)
async def edit_profile_page(request: Request, decoded_token=Depends(verify_token)):
    uid = decoded_token.get("uid")
    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_doc.to_dict()
    return templates.TemplateResponse("editprofile.html", {
        "request": request,
        "username": user.get("username", ""),
        "full_name": user.get("name", ""),
        "bio": user.get("bio", ""),
        "profile_pic_url": user.get("profile_pic_url", "/static/images/placeholder.png")
    })

from fastapi import status

from fastapi import status, HTTPException

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    try:
        decoded_token = await verify_token(request)
    except HTTPException as e:
        if e.status_code == 401 and e.detail == "Missing or invalid Authorization token":
            return templates.TemplateResponse("login.html", {"request": request})
        else:
            raise e

    uid = decoded_token.get("uid")

    # Get the list of usernames the current user follows
    following_ref = db.collection("User").document(uid).collection("following")
    following_docs = list(following_ref.stream())
    following_usernames = []
    users_ref = db.collection("User")
    for doc in following_docs:
        followee_doc = users_ref.document(doc.id).get()
        if followee_doc.exists:
            followee_data = followee_doc.to_dict()
            username = followee_data.get("username")
            if username:
                following_usernames.append(username)

    # Get current user's username
    current_user_doc = db.collection("User").document(uid).get()
    current_username = None
    if current_user_doc.exists:
        current_username = current_user_doc.to_dict().get("username")
    if current_username:
        following_usernames.append(current_username)

    # Query posts where Username in following_usernames, ordered by Date descending, limit 50
    posts_ref = db.collection("Post")
    posts = []
    chunk_size = 10
    for i in range(0, len(following_usernames), chunk_size):
        chunk = following_usernames[i:i+chunk_size]
        query = posts_ref.where("Username", "in", chunk).order_by("Date", direction=firestore.Query.DESCENDING).limit(50)
        posts_docs = query.stream()
        for doc in posts_docs:
            post = doc.to_dict()
            post['postId'] = doc.id
            posts.append(post)

    # Sort all posts by Date descending (in case multiple chunks)
    posts.sort(key=lambda x: x.get("Date", None), reverse=True)

    # Limit to last 50 posts
    posts = posts[:50]

    # For each post, ensure profilePicUrl is set, fallback to user's profile_pic_url if missing
    for post in posts:
        post["username"] = post.get("Username", "User")
        if not post.get("profilePicUrl"):
            # Fetch user's profile_pic_url from User collection
            user_query = db.collection("User").where("username", "==", post["username"]).limit(1).stream()
            user_doc = None
            for doc in user_query:
                user_doc = doc
                break
            if user_doc:
                user_data = user_doc.to_dict()
                post["profilePicUrl"] = user_data.get("profile_pic_url", "/static/images/placeholder.png")
            else:
                post["profilePicUrl"] = "/static/images/placeholder.png"

        # Fetch likes count and whether current user liked the post
        post_ref = db.collection("Post").document(post['postId'])
        likes_docs = list(post_ref.collection("likes").stream())
        post["likes_count"] = len(likes_docs)
        post["user_liked"] = any(doc.id == uid for doc in likes_docs)

        # Fetch latest 5 comments ordered by createdAt descending
        comments_ref = post_ref.collection("comments")
        comments_query = comments_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(5)
        comments_docs = list(comments_query.stream())
        comments = []
        for doc in comments_docs:  # newest first
            comment = doc.to_dict()
            user_id = comment.get("userId")
            profile_pic_url = comment.get("profilePicUrl", "/static/images/placeholder.png")
            username = "User"
            if user_id:
                user_doc = db.collection("User").document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    username = user_data.get("username", "User")
                    profile_pic_url = user_data.get("profile_pic_url", profile_pic_url)
            comment["username"] = username
            comment["profilePicUrl"] = profile_pic_url
            # Convert Firestore timestamps to ISO strings for JSON serialization
            created_at = comment.get("createdAt")
            if created_at:
                comment["createdAt"] = created_at.isoformat()
            comments.append(comment)

        post["comments"] = comments

        # Debug print comments data for verification
        print(f"Post ID: {post['postId']} Comments:")
        for c in comments:
            print(f"  UserId: {c.get('userId')}, Username: {c.get('username')}, Text: {c.get('text')}")

        # Fetch total comments count for the post
        total_comments_count = len(list(comments_ref.stream()))
        post["total_comments_count"] = total_comments_count

    return templates.TemplateResponse("home.html", {
        "request": request,
        "posts": posts
    })

@app.post("/api/follow/{username}")
async def follow_user(username: str, decoded_token=Depends(verify_token)):
    uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    users_ref = db.collection("User")

    # Get current user document by UID
    current_user_ref = users_ref.document(uid)
    current_user_doc = current_user_ref.get()
    if not current_user_doc.exists:
        return JSONResponse(content={"success": False, "error": "Current user not found"}, status_code=404)
    current_user = current_user_doc.to_dict()

    # Get target user document by username
    query = users_ref.where("username", "==", username).limit(1).stream()
    target_user_doc = None
    for doc in query:
        target_user_doc = doc
        break
    if not target_user_doc:
        return JSONResponse(content={"success": False, "error": "User to follow not found"}, status_code=404)
    target_user = target_user_doc.to_dict()

    target_user_ref = users_ref.document(target_user_doc.id)

    # Prevent following self
    target_email = target_user.get("email")
    if not target_email:
        return JSONResponse(content={"success": False, "error": "Target user email not found"}, status_code=500)

    if target_email == email:
        return JSONResponse(content={"success": False, "error": "Cannot follow yourself"}, status_code=400)

    # Check if current user is already following target user by checking followers subcollection
    followers_ref = target_user_ref.collection("followers")
    following_ref = current_user_ref.collection("following")

    follower_doc = followers_ref.document(uid)
    following_doc = following_ref.document(target_user_ref.id)

    follower_snapshot = follower_doc.get()
    is_following = follower_snapshot.exists

    if is_following:
        # Unfollow: remove documents from followers and following subcollections
        follower_doc.delete()
        following_doc.delete()
        is_following = False
    else:
        # Follow: add documents to followers and following subcollections with timestamp
        from google.cloud import firestore
        follower_doc.set({
            "email": email,
            "followedAt": firestore.SERVER_TIMESTAMP
        })
        following_doc.set({
            "email": target_email,
            "followedAt": firestore.SERVER_TIMESTAMP
        })
        is_following = True

    # Count followers of current user after update
    current_user_followers_ref = current_user_ref.collection("followers")
    current_user_followers_count = len(list(current_user_followers_ref.stream()))
    # Count following of current user after update
    current_user_following_ref = current_user_ref.collection("following")
    current_user_following_count = len(list(current_user_following_ref.stream()))

    # Count followers and following of target user after update
    target_user_followers_ref = target_user_ref.collection("followers")
    target_user_followers_count = len(list(target_user_followers_ref.stream()))
    target_user_following_ref = target_user_ref.collection("following")
    target_user_following_count = len(list(target_user_following_ref.stream()))

    return JSONResponse(content={
        "success": True,
        "is_following": is_following,
        "current_user_followers_count": current_user_followers_count,
        "current_user_following_count": current_user_following_count,
        "target_user_followers_count": target_user_followers_count,
        "target_user_following_count": target_user_following_count
    })

from fastapi import Form, UploadFile, File

from fastapi.responses import RedirectResponse

@app.post("/create_post")
async def create_post(
    request: Request,
    image: UploadFile = File(...),
    caption: str = Form(...),
    decoded_token=Depends(verify_token)
):
    uid = decoded_token.get("uid")

    # Validate file extension
    allowed_extensions = {".png", ".jpg", ".jpeg"}
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in allowed_extensions:
        error_message = "Invalid file type. Only PNG and JPG images are allowed."
        return templates.TemplateResponse("post.html", {"request": request, "error_message": error_message})

    # Validate content type
    allowed_content_types = {"image/png", "image/jpeg"}
    if image.content_type not in allowed_content_types:
        error_message = "Invalid file type. Only PNG and JPG images are allowed."
        return templates.TemplateResponse("post.html", {"request": request, "error_message": error_message})

    try:
        unique_filename = f"{uuid.uuid4()}{ext}"
        blob = bucket.blob(f"posts/{unique_filename}")

        # Upload image file to Firebase Storage
        blob.upload_from_file(image.file, content_type=image.content_type)
        blob.make_public()
        post_url = blob.public_url

        # Create Firestore document in posts collection
        posts_ref = db.collection("Post")
        new_post_ref = posts_ref.document()

        # Fetch username from User collection
        user_ref = db.collection("User").document(uid)
        user_doc = user_ref.get()
        username = ""
        if user_doc.exists:
            user_data = user_doc.to_dict()
            username = user_data.get("username", "")

        new_post_ref.set({
            "postUrl": post_url,
            "caption": caption,
            "Date": firestore.SERVER_TIMESTAMP,
            "userId": uid,
            "Username": username
        })

        # Create empty likes and comments subcollections with placeholder docs
        new_post_ref.collection("likes").document("_init").set({"initialized": True})
        new_post_ref.collection("comments").document("_init").set({"initialized": True})

        # Delete placeholder docs to keep subcollections empty
        new_post_ref.collection("likes").document("_init").delete()
        new_post_ref.collection("comments").document("_init").delete()

        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        print(f"Error creating post: {e}")
        return templates.TemplateResponse("post.html", {"request": request, "error_message": "Failed to create post"})

from fastapi import Path

from fastapi import Body

@app.post("/api/posts/{post_id}/toggle_like")
async def toggle_like(
    post_id: str,
    decoded_token=Depends(verify_token)
):
    uid = decoded_token.get("uid")
    post_ref = db.collection("Post").document(post_id)
    like_ref = post_ref.collection("likes").document(uid)

    like_doc = like_ref.get()
    if like_doc.exists:
        # Unlike
        like_ref.delete()
        liked = False
    else:
        # Like
        like_ref.set({"likedAt": firestore.SERVER_TIMESTAMP})
        liked = True

    # Count likes after update
    likes_count = len(list(post_ref.collection("likes").stream()))

    return JSONResponse({"success": True, "liked": liked, "likes_count": likes_count})

from fastapi import Form
from fastapi.responses import RedirectResponse

@app.post("/toggle_like/{post_id}")
async def toggle_like_form(post_id: str, redirect_url: str = Form(None), decoded_token=Depends(verify_token)):
    uid = decoded_token.get("uid")
    post_ref = db.collection("Post").document(post_id)
    like_ref = post_ref.collection("likes").document(uid)

    like_doc = like_ref.get()
    if like_doc.exists:
        like_ref.delete()
    else:
        like_ref.set({"likedAt": firestore.SERVER_TIMESTAMP})

    # Redirect to the provided redirect_url or default to viewpost page for the post
    if not redirect_url:
        redirect_url = f"/viewpost/{post_id}"

    return RedirectResponse(url=redirect_url, status_code=303)

from fastapi import Form

@app.post("/add_comment/{post_id}")
async def add_comment_form(
    post_id: str,
    comment: str = Form(...),
    redirect_url: str = Form(None),
    decoded_token=Depends(verify_token)
):
    uid = decoded_token.get("uid")
    text = comment.strip()
    if not text:
        return RedirectResponse(url=redirect_url or "/", status_code=303)

    # Limit comment length to 200 characters
    if len(text) > 200:
        text = text[:200]

    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return RedirectResponse(url=redirect_url or "/", status_code=303)
    user = user_doc.to_dict()

    try:
        comment_ref = db.collection("Post").document(post_id).collection("comments").document()
        comment_ref.set({
            "text": text,
            "userId": uid,
            "profilePicUrl": user.get("profile_pic_url", "/static/images/placeholder.png"),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error adding comment: {e}")

    return RedirectResponse(url=redirect_url or "/", status_code=303)

@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: str,
    data: dict = Body(...),
    decoded_token=Depends(verify_token)
):
    uid = decoded_token.get("uid")
    text = data.get("text", "").strip()
    if not text:
        return JSONResponse({"success": False, "error": "Comment text is required"}, status_code=400)

    # Limit comment length to 200 characters
    if len(text) > 200:
        text = text[:200]

    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return JSONResponse({"success": False, "error": "User not found"}, status_code=404)
    user = user_doc.to_dict()

    try:
        comment_ref = db.collection("Post").document(post_id).collection("comments").document()
        comment_ref.set({
            "text": text,
            "username": user.get("username", ""),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error adding comment: {e}")
        return JSONResponse({"success": False, "error": "Failed to add comment"}, status_code=500)

    return JSONResponse({"success": True})

from google.cloud.firestore_v1 import SERVER_TIMESTAMP

@app.get("/api/posts/{post_id}/comments")
async def get_all_comments(
    post_id: str,
    decoded_token=Depends(verify_token)
):
    comments_ref = db.collection("Post").document(post_id).collection("comments")
    comments_query = comments_ref.order_by("createdAt", direction=firestore.Query.DESCENDING)
    comments_docs = list(comments_query.stream())
    comments = []
    for doc in comments_docs:  # newest first
        comment = doc.to_dict()
        user_id = comment.get("userId")
        profile_pic_url = comment.get("profilePicUrl", "/static/images/placeholder.png")
        username = "User"
        if user_id:
            user_doc = db.collection("User").document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                username = user_data.get("username", "User")
                profile_pic_url = user_data.get("profile_pic_url", profile_pic_url)
        comment["username"] = username
        comment["profilePicUrl"] = profile_pic_url
        # Convert Firestore timestamp to ISO string for JSON serialization
        created_at = comment.get("createdAt")
        if created_at:
            comment["createdAt"] = created_at.isoformat()
        comments.append(comment)

    return JSONResponse({"success": True, "comments": comments})

from fastapi import Path

@app.get("/viewpost/{post_id}", response_class=HTMLResponse)
async def view_post_page(
    request: Request,
    post_id: str = Path(...),
    decoded_token=Depends(verify_token)
):
    uid = decoded_token.get("uid")

    # Fetch post document
    post_ref = db.collection("Post").document(post_id)
    post_doc = post_ref.get()
    if not post_doc.exists:
        raise HTTPException(status_code=404, detail="Post not found")
    post = post_doc.to_dict()

    # Set username field from Firestore "Username" field for template
    post['username'] = post.get('Username', 'User')

    # Fetch user's profile_pic_url from User collection for profilePicUrl
    users_ref = db.collection("User")
    user_query = users_ref.where("username", "==", post['username']).limit(1).stream()
    user_doc = None
    for doc in user_query:
        user_doc = doc
        break
    if user_doc:
        user_data = user_doc.to_dict()
        post['profilePicUrl'] = user_data.get("profile_pic_url", "/static/images/placeholder.png")
    else:
        post['profilePicUrl'] = "/static/images/placeholder.png"

    # Fetch likes count
    likes_ref = post_ref.collection("likes")
    likes_docs = list(likes_ref.stream())
    likes_count = len(likes_docs)

    # Check if current user liked the post
    user_liked = any(doc.id == uid for doc in likes_docs)

    # Fetch latest 5 comments ordered by createdAt descending
    comments_ref = post_ref.collection("comments")
    comments_query = comments_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(5)
    comments_docs = list(comments_query.stream())
    comments = []
    for doc in comments_docs:  # newest first
        comment = doc.to_dict()
        user_id = comment.get("userId")
        profile_pic_url = comment.get("profilePicUrl", "/static/images/placeholder.png")
        username = "User"
        if user_id:
            user_doc = db.collection("User").document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                username = user_data.get("username", "User")
                profile_pic_url = user_data.get("profile_pic_url", profile_pic_url)
        comment["username"] = username
        comment["profilePicUrl"] = profile_pic_url

        # Convert Firestore timestamp to ISO string for JSON serialization
        created_at = comment.get("createdAt")
        if created_at:
            comment["createdAt"] = created_at.isoformat()
        comments.append(comment)

    return templates.TemplateResponse("viewpost.html", {
        "request": request,
        "post": post,
        "post_id": post_id,
        "likes_count": likes_count,
        "user_liked": user_liked,
        "comments": comments,
        "current_user_id": uid
    })

@app.get("/post.html", response_class=HTMLResponse)
async def post_page(request: Request, decoded_token=Depends(verify_token)):
    return templates.TemplateResponse("post.html", {"request": request})

@app.get("/editpost.html", response_class=HTMLResponse)
async def edit_post_page(request: Request, post_id: str, decoded_token=Depends(verify_token)):
    post_ref = db.collection("Post").document(post_id)
    post_doc = post_ref.get()
    if not post_doc.exists:
        raise HTTPException(status_code=404, detail="Post not found")
    post = post_doc.to_dict()

    # Verify ownership
    uid = decoded_token.get("uid")
    if post.get("userId") != uid:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return templates.TemplateResponse("editpost.html", {
        "request": request,
        "post": post,
        "post_id": post_id
    })

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    return response

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, decoded_token=Depends(verify_token)):
    uid = decoded_token.get("uid")
    user_ref = db.collection("User").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_doc.to_dict()

    # Fetch posts by user using Username instead of userId
    posts_ref = db.collection("Post")
    query_posts = posts_ref.where("Username", "==", user.get("username")).order_by("Date", direction=firestore.Query.DESCENDING)
    posts_docs = query_posts.stream()
    posts = []
    for doc in posts_docs:
        post = doc.to_dict()
        post['postId'] = doc.id
        posts.append(post)

    followers_ref = user_ref.collection("followers")
    following_ref = user_ref.collection("following")

    followers_count = len(list(followers_ref.stream()))
    following_count = len(list(following_ref.stream()))

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "username": user.get("username", ""),
        "full_name": user.get("name", ""),
        "bio": user.get("bio", ""),
        "profile_pic_url": user.get("profile_pic_url", ""),
        "posts": posts,
        "posts_count": len(posts),
        "followers_count": followers_count,
        "following_count": following_count,
        "is_own_profile": True
    })
