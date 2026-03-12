console.log("🔥 HMS SERVER RUNNING 🔥");

// ================= IMPORTS =================

const express = require("express");
const cors = require("cors");
const mongoose = require("mongoose");
const path = require("path");

const app = express();


// ================= MIDDLEWARE =================

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname)); // serve index.html


// ================= MONGODB CONNECTION =================

mongoose.connect("mongodb://localhost:27017/men_sys")

.then(()=>console.log("✅ MongoDB Connected"))

.catch(err=>console.log("❌ MongoDB Error:",err));


// ================= USER SCHEMA =================

const User = mongoose.model("User",{

name:String,
username:String,
password:String,
role:String

});


// ================= DOCTOR SCHEMA =================

const Doctor = mongoose.model("Doctor",{

name:String,
username:String,
password:String,
specialization:String,
phone:String,
status:Number

});


// ================= USER REGISTER =================

app.post("/register", async (req,res)=>{

console.log("📝 USER REGISTER DATA:", req.body);

const { name, username, password, role } = req.body;

try{

const checkUser = await User.findOne({username});

if(checkUser){

return res.json({
success:false,
message:"❌ Username already exists"
});
}

await User.create({name,username,password,role});

res.json({
success:true,
message:"✅ Registered Successfully"
});

}catch(err){

console.log("❌ REGISTER ERROR:",err);

res.json({
success:false,
message:"❌ Registration Failed"
});

}

});


// ================= DOCTOR REGISTER =================

app.post("/registerDoctor", async(req,res)=>{

console.log("👨‍⚕️ DOCTOR REGISTER DATA:", req.body);

const { name, username, password, specialization, phone } = req.body;

try{

await Doctor.create({

name,
username,
password,
specialization,
phone,
status:0

});

res.json({
success:true,
message:"✅ Doctor Registered Successfully"
});

}catch(err){

console.log("❌ DOCTOR REGISTER ERROR:",err);

res.json({
success:false,
message:"❌ Doctor Registration Failed"
});

}

});


// ================= LOGIN =================

app.post("/login", async(req,res)=>{

console.log("🔐 LOGIN DATA:", req.body);

const { username, password } = req.body;

try{

const user = await User.findOne({username,password});

if(user){

res.json({
success:true,
message:"✅ Login Successful",
user:user
});

}else{

res.json({
success:false,
message:"❌ Invalid Login"
});

}

}catch(err){

console.log("❌ LOGIN ERROR:",err);

res.json({
success:false,
message:"❌ Login Error"
});

}

});


// ================= START SERVER =================

app.listen(3000,()=>{

console.log("🚀 Server running on http://localhost:3000");

});
