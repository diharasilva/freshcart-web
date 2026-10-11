"""Seed local demo users. Run: flask --app app seed-demo (after schema import)."""
import click
from werkzeug.security import generate_password_hash
from app import app, mysql

@app.cli.command("seed-demo")
def seed_demo():
    """Create demo customer/admin accounts if absent; change passwords immediately."""
    users=[('FreshCart Admin','admin@freshcart.local','Admin123!','admin'),('Demo Customer','customer@freshcart.local','Customer123!','customer')]
    cur=mysql.connection.cursor()
    for name,email,password,role in users:
        cur.execute('SELECT id FROM users WHERE email=%s',(email,))
        if not cur.fetchone(): cur.execute('INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,%s)',(name,email,generate_password_hash(password),role))
    mysql.connection.commit(); cur.close()
    click.echo('Demo users ready: admin@freshcart.local / Admin123! and customer@freshcart.local / Customer123!')
