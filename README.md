# Luxent
This project was the final task for the CS50x Course! 
#### Description:
This web application is for a local rental car company. Supports both client and admin sides, and it's made using Python, Flask, Bootstrap, JavaScript, HTML, CSS, and Jinja; also, the app is responsive.

The client can make a reservation by choosing one of the vehicles listed or filtering by engine type, color, or car type and see all his reservations made; also, to make a reservation he has to be logged in; if he doesn't have an account, he can register.

The admin can remove a reservation made by any account, add a car, change its details or remove one, add and remove contracts, or add a new admin.

Both types of accounts can change their passwords even if they aren't logged in; see the about page, contact page, and FAQ page even if they are logged in or not.

The project contains two folders, two Python files, and a database. The folders are called templates and static. The static folder contains an images folder that has in it all the images used in the project, a JavaScript file, and a CSS file. The JavaScript file contains a function that gives the navigation bar a background color when scrolled. The CSS file contains elements that override some of Bootstrap's colors and elements; that way the project is more personalized. 

The templates folder contains all the HTML templates used in this project. There are 20 templates for the admin side and client side. The main templates are:

* layout
* index
* reservations
* register
* login
* all_reservations
* contracts
* cars
* change_password
* add_admin

The rest of them are forms or pages that only display basic information like sorry, about us, contact, etc. The layout, index, and reservations templates are the most important ones because they render the pages correctly. 

For example, layout.html provides the basic HTML document, which contains the head and the body. In the head is put the link to get all the frameworks, fonts, and so on, and in the body is the nav bar that changes based on the user type (admin or client). In the index.html is presented the main page of the web application. In the reservations template, the user can choose one preference from three different categories: engine, color, and car type, and also see the cars available.

In the Python file called help.py is a function that helps with the login system, more specifically keeping track of the user activity using two imports. The first one is Flask, and the second one is Functools.

In the other Python file is the main application, where the routes are made and all the logic behind this web application is. 

In this app were used many libraries and frameworks like datetime, SQL from CS50, Flask, and Werkzeug for hashing the passwords. The app has five routes for the client side, eight for the admin side, and five for both the client and admin side. 

Most of these routes are for different forms that the user completes and sends; all the inputs received have functionalities to handle errors by rendering an error message.

The most complex routes are the ones that handle the reservations and contracts because they have to put the data in a list and then render it. The reason why I choose this approach is because I had to see how many days and the total price of the renting is without registering in the database.

The last thing from this project is the database made with SQLite given by CS50. This database is called luxent.db and contains the following tables:

* users
* clients
* admins
* engine
* color
* car_type
* vehicles
* reservations
* contracts

The admins and clients tables are referencing the users table by the user_id. 

To reduce the complexity and make the filtering easier, I have created separate tables for each part: engine, color, and car type. They are connected to the vehicles table by IDs referencing each corresponding ID.

The reservations table is connected with the rest of the tables by the ID of the vehicle that the user wants and by the ID of the user, and the contracts table is connected with the rest of the tables only by the ID of the rented vehicle.

To make a reservation, the user has to register for an account; after making the account, the user has to complete a reservation form, adding its first and last name, phone number, vehicle ID, start date, and end date of the reservation. After making it, the new reservation will appear in the admin side at the all reservations page. After that, the admin has to check if the vehicle is available in the said time; if so, the admin will call the client.

The admin can make an account for another admin, remove a reservation, add a car, change its details, or remove it, and also add or remove a contract.

Both sides can change their passwords at any time, even if they aren't logged in.
