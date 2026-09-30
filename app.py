import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

ROOT=os.path.abspath(os.path.dirname(__file__))
app=Flask(__name__)
app.config["SECRET_KEY"]=os.environ.get("SECRET_KEY","dev-secret-change-before-deploy")
app.config["SQLALCHEMY_DATABASE_URI"]=os.environ.get("DATABASE_URL","sqlite:///"+os.path.join(ROOT,"blog.db"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
db=SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(90),nullable=False)
    email=db.Column(db.String(160),unique=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)

class Post(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    title=db.Column(db.String(180),nullable=False)
    body=db.Column(db.Text,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    author=db.relationship("User",backref="posts")
    comments=db.relationship("Comment",backref="post",cascade="all, delete-orphan",order_by="Comment.created_at.asc()")

class Comment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    post_id=db.Column(db.Integer,db.ForeignKey("post.id"),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    body=db.Column(db.String(1200),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    author=db.relationship("User")

def user_now():
    uid=session.get("user_id")
    return db.session.get(User,uid) if uid else None

def login_required(fn):
    @wraps(fn)
    def inner(*args,**kwargs):
        if not user_now():
            flash("Please sign in to continue.","error")
            return redirect(url_for("login",next=request.path))
        return fn(*args,**kwargs)
    return inner

@app.context_processor
def inject_user(): return {"current_user":user_now()}

@app.route("/")
def index():
    posts=Post.query.order_by(Post.created_at.desc()).all()
    return render_template("index.html",posts=posts)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        if not name or not email or len(password)<8: flash("Enter your name, email and password (8+ characters).","error")
        elif User.query.filter_by(email=email).first(): flash("Email already registered.","error")
        else:
            u=User(name=name,email=email); u.set_password(password); db.session.add(u); db.session.commit(); session["user_id"]=u.id
            return redirect(url_for("index"))
    return render_template("auth.html",mode="register")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=User.query.filter_by(email=request.form.get("email","").strip().lower()).first()
        if u and u.check_password(request.form.get("password","")):
            session.clear(); session["user_id"]=u.id; return redirect(request.args.get("next") or url_for("index"))
        flash("Email or password is incorrect.","error")
    return render_template("auth.html",mode="login")

@app.post("/logout")
def logout(): session.clear(); return redirect(url_for("index"))

@app.route("/post/new",methods=["GET","POST"])
@login_required
def new_post():
    if request.method=="POST":
        title=request.form.get("title","").strip(); body=request.form.get("body","").strip()
        if not title or not body: flash("A title and post content are required.","error")
        elif len(title)>180: flash("Title must be 180 characters or fewer.","error")
        else:
            post=Post(user_id=user_now().id,title=title,body=body); db.session.add(post); db.session.commit()
            flash("Your post is published.","success"); return redirect(url_for("view_post",post_id=post.id))
    return render_template("editor.html",post=None)

@app.route("/post/<int:post_id>")
def view_post(post_id):
    post=Post.query.get_or_404(post_id)
    return render_template("post.html",post=post)

@app.route("/post/<int:post_id>/edit",methods=["GET","POST"])
@login_required
def edit_post(post_id):
    post=Post.query.get_or_404(post_id)
    if post.user_id!=user_now().id:
        flash("You can only edit your own posts.","error"); return redirect(url_for("view_post",post_id=post.id))
    if request.method=="POST":
        title=request.form.get("title","").strip(); body=request.form.get("body","").strip()
        if not title or not body: flash("A title and post content are required.","error")
        elif len(title)>180: flash("Title must be 180 characters or fewer.","error")
        else:
            post.title=title; post.body=body; post.updated_at=datetime.utcnow(); db.session.commit()
            flash("Post updated.","success"); return redirect(url_for("view_post",post_id=post.id))
    return render_template("editor.html",post=post)

@app.post("/post/<int:post_id>/delete")
@login_required
def delete_post(post_id):
    post=Post.query.get_or_404(post_id)
    if post.user_id!=user_now().id: flash("You can only delete your own posts.","error")
    else: db.session.delete(post); db.session.commit(); flash("Post deleted.","success")
    return redirect(url_for("index"))

@app.post("/post/<int:post_id>/comment")
@login_required
def add_comment(post_id):
    post=Post.query.get_or_404(post_id); body=request.form.get("body","").strip()
    if not body: flash("Comment cannot be empty.","error")
    elif len(body)>1200: flash("Comment is too long (max 1200 characters).","error")
    else:
        db.session.add(Comment(post_id=post.id,user_id=user_now().id,body=body)); db.session.commit()
    return redirect(url_for("view_post",post_id=post.id)+"#comments")

@app.get("/api/posts")
def api_posts():
    return jsonify([{"id":p.id,"title":p.title,"body":p.body,"author":p.author.name,"created_at":p.created_at.isoformat(),"comment_count":len(p.comments)} for p in Post.query.order_by(Post.created_at.desc()).all()])

@app.get("/api/posts/<int:post_id>")
def api_post(post_id):
    p=Post.query.get_or_404(post_id)
    return jsonify({"id":p.id,"title":p.title,"body":p.body,"author":p.author.name,
                    "comments":[{"id":c.id,"author":c.author.name,"body":c.body,"created_at":c.created_at.isoformat()} for c in p.comments]})

@app.get("/api/health")
def health(): return jsonify({"status":"ok","app":"Thoughtline Blog"})

with app.app_context(): db.create_all()
if __name__=="__main__": app.run(debug=os.environ.get("FLASK_DEBUG","false").lower()=="true")
