from fastapi import FastAPI
from database import engine, Base
import models
from fastapi import File, UploadFile
import shutil
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi import Form
from fastapi.responses import RedirectResponse
from fastapi import Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from starlette.middleware.sessions import SessionMiddleware


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
templates = Jinja2Templates(directory="templates")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

@app.get("/admin", response_class=HTMLResponse)
def admin_login(request: Request):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {}
    )

@app.post("/admin-login")
def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["admin"] = True
        return RedirectResponse("/orders", status_code=303)

    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/upload", response_class=HTMLResponse)
def admin_upload_page(request: Request):

    if not request.session.get("admin"):
        return RedirectResponse("/admin", status_code=303)

    return templates.TemplateResponse(
        request,
        "admin_upload.html",
        {}
    )

@app.post("/admin/upload")
def admin_upload(
    request: Request,
    title: str = Form(...),
    price: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    if not request.session.get("admin"):
        return RedirectResponse("/admin", status_code=303)

    file_location = f"uploads/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_art = models.Artwork(
        title=title,
        price=price,
        image_url=f"/{file_location}",
        description="admin upload"
    )

    db.add(new_art)
    db.commit()

    return RedirectResponse("/orders", status_code=303)


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):

    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=303)

    artworks = db.query(models.Artwork).all()

    return templates.TemplateResponse(
        request,
        "gallery.html",
        {"artworks": artworks}
    )

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {}
    )

@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.password == password
    ).first()

    if user:
        request.session["user"] = username
        return RedirectResponse("/", status_code=303)

    return RedirectResponse("/login", status_code=303)

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(
        request,
        "signup.html",
        {}
    )

@app.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = models.User(username=username, password=password)

    db.add(user)
    db.commit()

    return RedirectResponse("/login", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)




@app.post("/artworks")
def create_artwork(title: str, price: int, db: Session = Depends(get_db)):
    new_art = models.Artwork(
        title=title,
        price=price,
        image_url="test.jpg",
        description="sample"
    )
    
    db.add(new_art)
    db.commit()
    db.refresh(new_art)

    return new_art

@app.get("/artworks")
def get_artworks(db: Session = Depends(get_db)):
    artworks = db.query(models.Artwork).all()
    return artworks

@app.post("/upload-artwork")
def upload_artwork(
    title: str,
    price: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_location = f"uploads/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_art = models.Artwork(
    title=title,
    price=price,
    image_url=f"http://127.0.0.1:8000/{file_location}",
    description="uploaded image"
)

    db.add(new_art)
    db.commit()
    db.refresh(new_art)

    return new_art

@app.get("/gallery", response_class=HTMLResponse)
def gallery(request: Request, db: Session = Depends(get_db)):
    artworks = db.query(models.Artwork).all()

    return templates.TemplateResponse(
        request,
        "gallery.html",
        {"artworks": artworks}
    )

@app.get("/buy/{art_id}", response_class=HTMLResponse)
def buy_page(art_id: int, request: Request, db: Session = Depends(get_db)):
    art = db.query(models.Artwork).filter(models.Artwork.id == art_id).first()

    return templates.TemplateResponse(
        request,
        "buy.html",
        {"art": art}
    )

@app.post("/place-order")
def place_order(
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    art_id: int = Form(...),
    db: Session = Depends(get_db)
):
    order = models.Order(
        name=name,
        phone=phone,
        address=address,
        art_id=art_id
    )

    db.add(order)
    db.commit()
    return RedirectResponse(url="/success", status_code=303)

@app.get("/success", response_class=HTMLResponse)
def success_page(request: Request):
    return templates.TemplateResponse(
        request,
        "success.html",
        {}
    )

@app.get("/orders", response_class=HTMLResponse)
def view_orders(request: Request, db: Session = Depends(get_db)):

    if not request.session.get("admin"):
        return RedirectResponse("/admin", status_code=303)

    orders = db.query(models.Order).all()
    artworks = db.query(models.Artwork).all()

    art_dict = {
        a.id: {
            "title": a.title,
            "image": a.image_url
        }
        for a in artworks
    }

    return templates.TemplateResponse(
        request,
        "orders.html",
        {
            "orders": orders,
            "art_dict": art_dict
        }
    )