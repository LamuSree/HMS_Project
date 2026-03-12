console.log("🔥 HMS SERVER RUNNING 🔥");

// ================= IMPORTS =================

const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");
const path = require("path");

const app = express();

// ================= MIDDLEWARE =================

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname)); // serve index.html

// ================= POSTGRES CONNECTION =================

const pool = new Pool({
    user: "postgres",
    host: "localhost",
    database: "men_sys",          // ✅ your actual database
    password: "postgres123",      // ✅ your password
    port: 5432,
});

// ✅ CHECK WHICH DATABASE IS CONNECTED
pool.query("SELECT current_database()")
    .then(r => console.log("✅ CONNECTED DB:", r.rows[0].current_database))
    .catch(err => console.log("❌ DB CHECK ERROR:", err));

// Test DB connection
pool.connect()
    .then(() => console.log("✅ Database Connected"))
    .catch(err => console.log("❌ DB Connection Error:", err));

// ================= REGISTER API =================

app.post("/register", async (req, res) => {

    // ✅ DEBUG: see what data comes from form
    console.log("📝 REGISTER DATA:", req.body);

    const { name, username, password, role } = req.body;

    try {

        // Check if username already exists
        const checkUser = await pool.query(
            "SELECT * FROM users WHERE username=$1",
            [username]
        );

        if (checkUser.rows.length > 0) {
            return res.json({ message: "❌ Username already exists" });
        }

        // Insert new user
        await pool.query(
            "INSERT INTO users(name, username, password, role) VALUES ($1,$2,$3,$4)",
            [name, username, password, role]
        );

        res.json({ message: "✅ Registered Successfully" });

    } catch (err) {
        console.log("❌ REGISTER ERROR:", err);
        res.json({ message: "❌ Registration Failed" });
    }
});

// ================= LOGIN API =================

app.post("/login", async (req, res) => {
  console.log("🔐 LOGIN DATA:", req.body);

  

    // ✅ DEBUG: see login data
    

    const { username, password } = req.body;

    try {

        const result = await pool.query(
            "SELECT * FROM users WHERE username=$1 AND password=$2",
            [username, password]
        );

        if (result.rows.length > 0) {

            res.json({
                message: "✅ Login Successful",
                user: result.rows[0]
            });

        } else {

            res.json({
                message: "❌ Invalid Login"
            });

        }

    } catch (err) {
        console.log("❌ LOGIN ERROR:", err);
        res.json({ message: "❌ Login Error" });
    }

});

// ================= START SERVER =================

app.listen(3000, () => {
    console.log("🚀 Server running on http://localhost:3000");
});
