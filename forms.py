from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Regexp


# ================= REGISTER FORM =================

class RegisterForm(FlaskForm):

    # ⭐ Username validation
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=50),
            Regexp(
                r'^[A-Z][a-zA-Z]*$',
                message="Username must start with capital letter and contain only letters"
            )
        ]
    )

    # ⭐ Gmail-only validation
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(),
            Regexp(
                r'^[a-zA-Z0-9._%+-]+@gmail\.com$',
                message="Email must be a Gmail address"
            )
        ]
    )

    # ⭐ Strong password validation
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Regexp(
                r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!@$%^&*_]).{8,}$',
                message="Password must contain uppercase, lowercase, number and special character (!@$%^&*_)"
            )
        ]
    )

    # ⭐ Confirm password
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match")
        ]
    )

    role = SelectField(
        "Role",
        choices=[
            ("Admin", "Admin"),
            ("Doctor", "Doctor"),
            ("Nurse", "Nurse"),
            ("User", "User")
        ],
        validators=[DataRequired()]
    )

    # ⭐ Specialization field
    specialization = StringField("Specialization")

    submit = SubmitField("Sign Up")

    # ⭐ CUSTOM VALIDATION
    def validate_specialization(self, field):

        # Only Doctor must fill specialization
        if self.role.data == "Doctor" and not field.data:
            raise ValidationError("Specialization is required for Doctor role")


# ================= LOGIN FORM =================

class LoginForm(FlaskForm):

    username = StringField(
        "Username",
        validators=[DataRequired()]
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    submit = SubmitField("Login")
