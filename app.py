from flask import Flask, render_template, redirect, flash, session
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, DecimalField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_sqlalchemy import SQLAlchemy   
from flask import request, url_for
from sendgridmail import sendmail
import ibm_db
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRETKEY'

conn = ibm_db.connect(os.getenv('IBM_DB_CONNECTION'), "", "")

class Expense():
    def __repr__(self) -> str:
        pass

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __repr__(self) -> str:
        return f"LoginForm(, '{self.email}')"

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __repr__(self) -> str:
        return f"RegisterForm('{self.name}', '{self.email}')"

class ExpenseForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired()])
    date = DateField('Date')
    submit = SubmitField('Submit')

    def __repr__(self):
        return f"ExpenseForm('{self.title}', '{self.category}', {self.amount}, {s.date})"

@app.route("/delete/<int:expense_id>", methods=['POST'])
def delete(expense_id):
    delete_query = ibm_db.exec_immediate(conn, f"delete from expense where id={expense_id}")
    return redirect(url_for('home'))

@app.route("/update/<int:expense_id>", methods=['GET', 'POST'])
def update(expense_id):
    form = ExpenseForm()
        # if the form is validated and submited, update the data of the item
        # with the data from the field
    if form.validate_on_submit():
        title = form.title.data
        category = form.category.data
        amount = form.amount.data
        date = form.date.data
        sql = f"update expense set title = '{title}', category = '{category}', amount = {amount}, date = '{date}' where id = {expense_id}"
        udpate = ibm_db.exec_immediate(conn, sql)
        return redirect(url_for('home'))
        # populate the field with data of the chosen expense 
    elif request.method == 'GET':
        sql = f"select * from expense where id = {expense_id}"
        select = ibm_db.exec_immediate(conn, sql)
        tuple = ibm_db.fetch_tuple(select)
        form.title.data = tuple[1]
        form.category.data = tuple[2]
        form.amount.data = tuple[3]
        form.date.data = tuple[4]
    return render_template('add.html', form=form, title='Edit Expense')

@app.route('/add', methods=['GET', 'POST'])
def add():
    form = ExpenseForm()
    #if form successfully validated
    if form.validate_on_submit():
        # we create an expense object
        insert_query = ibm_db.exec_immediate(conn, f"insert into expense(title, category, amount, date, email) values('{form.title.data}', '{form.category.data}', '{form.amount.data}', '{form.date.data}', '{session['user']}')")
        sendmail('vsrivathsan@student.tce.edu', 'Expense added successfully', f'Title: {form.title.data}\nCategory: {form.category.data}\nAmount: {form.amount.data}\nDate: {form.date.data}\n')
        # add it to the database
        return redirect('/home')

    form.date.data = datetime.utcnow()
    return render_template('add.html', form=form)

@app.route('/logout')
def logout():
    session['user'] = ""
    session['name'] = ""
    flash('Logged out', 'message')
    return redirect('/login')

@app.route('/login',methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        select = ibm_db.exec_immediate(conn, f"select name, password from user where email = '{form.email.data}'")
        tup = ibm_db.fetch_tuple(select)
        if tup == False:
            flash('Account does not exist.. Register')
            return redirect('/register')
        if tup[1] == form.password.data:
            session['user'] = form.email.data
            session['name'] = tup[0]
            flash(f'Login Successful', 'message')
            return redirect('/home')
        else:
            flash('Invalid credentials', 'message')
            return redirect('/login')
    return render_template('login.html', form=form)

@app.route('/register',methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # we create an expense object
        select = ibm_db.exec_immediate(conn, f"select name, password from user where email = '{form.email.data}'")
        tup = ibm_db.fetch_tuple(select)
        if tup  :
            flash('Account already exists. Login', 'message')
            return redirect('/login')
        try: 
            insert_query = ibm_db.exec_immediate(conn, f"insert into user values('{form.name.data}', '{form.email.data}', '{form.password.data}')")
            sendmail(form.email.data, 'Registration Successful', f'Hi {form.name.data},\n\tYour account has been created successfully...')          
            # add it to the database
            session['user'] = form.email.data
            session['name'] = form.name.data
            flash('Registration successful', 'message')
            flash('Start adding your expenses', 'message')
            return redirect('/home')
        except:
            flash(e, 'error')
    return render_template('register.html', form=form)

@app.route('/home')
@app.route('/')
def home():
    print(session['user'] == "")
    if session['user'] == "":
        return redirect('/login')

    all_expenses = []
    sql = f"select * from expense where email = '{session['user']}' order by date desc"
    select = ibm_db.exec_immediate(conn, sql)
    tuple = ibm_db.fetch_tuple(select)

    while tuple != False:
        exp = Expense()
        exp.id = tuple[0] 
        exp.title = tuple[1] 
        exp.category = tuple[2]
        exp.amount = tuple[3]
        exp.date = tuple[4]
        all_expenses.append(exp)
        tuple = ibm_db.fetch_tuple(select)
    return render_template('home.html', expenses=all_expenses, data = session['name'])

if __name__ == '__main__':
    app.run(debug=True)