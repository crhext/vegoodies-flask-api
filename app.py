from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os
import boto3
import random
from config import S3_BUCKET, S3_KEY, S3_SECRET, PSQL_DEV, PSQL_PRD
from flask_cors import CORS, cross_origin

##aws authenticate
s3 = boto3.client(
	's3',
	aws_access_key_id=S3_KEY,
	aws_secret_access_key=S3_SECRET,
	region_name='eu-west-2')

## init app
app = Flask(__name__)

##allows for cross origin api calls
cors = CORS(app, resources={r"*": {"origins": "*"}})

##gets base dir
basedir = os.path.abspath(os.path.dirname(__file__))

##database
ENV = 'prod'
if ENV == 'dev':
	app.debug = True
	app.config['SQLALCHEMY_DATABASE_URI'] = PSQL_DEV
else:
	app.debug = False
	app.config['SQLALCHEMY_DATABASE_URI'] = PSQL_PRD
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

##init db
db = SQLAlchemy(app)

#init ma
ma = Marshmallow(app)

##recipe class/model 
class Recipe(db.Model):
	__tablename__ = 'recipes'
	id = db.Column(db.Integer, primary_key=True)
	recipe_type = db.Column(db.String(30))
	title = db.Column(db.String(100))
	name = db.Column(db.String(100), unique=True)
	overview = db.Column(db.String(5000))
	method = db.Column(db.String(20000))
	ingredients = db.Column(db.String(20000))
	tags = db.Column(db.String(5000))
	portions = db.Column(db.String(200))
	author = db.Column(db.String(100))
	image = db.Column(db.String(100))

	def __init__(self, recipe_type, title, name, overview, method, ingredients, tags, portions, author, image):
		self.recipe_type = recipe_type
		self.title = title
		self.name = name
		self.overview = overview
		self.method = method
		self.ingredients = ingredients
		self.tags = tags
		self.portions = portions
		self.author = author
		self.image = image

##recipe schema
class RecipeSchema(ma.Schema):
	class Meta:
		fields = ('id', 'recipe_type', 'title', 'name', 'overview', 'method', 'ingredients', 'tags', 'portions', 'author', 'image')

##init schema
recipe_schema = RecipeSchema()
recipes_schema = RecipeSchema(many=True)

##create recipe
@app.route('/recipe',methods=['POST'])
def add_recipe():

	try: 
		title = request.form['title']
		recipe_type = request.form['recipe_type']
		name = request.form['title'].replace(' ','').lower()
		overview = request.form['overview']
		method = request.form['method']
		ingredients = request.form['ingredients']
		tags = request.form['tags']
		portions = request.form['portions']
		author = request.form['author']

		if request.files['image']:
			file = request.files['image']
			image = file.filename

			s3_resource = boto3.resource('s3',
				aws_access_key_id=S3_KEY,
				aws_secret_access_key=S3_SECRET,
				region_name='eu-west-2')
			my_bucket = s3_resource.Bucket(S3_BUCKET)
			my_bucket.Object(file.filename).put(Body=file)
		else:
			image = ""


		new_recipe = Recipe(recipe_type, title, name, overview, method, ingredients, tags, portions, author, image)
		db.session.add(new_recipe)
		db.session.commit()
		response = recipe_schema.jsonify(new_recipe)
		response.headers['Access-Control-Allow-Origin'] = '*'
		response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
		response.headers['Access-Control-Allow-Methods'] = 'OPTIONS, HEAD, GET, POST, DELETE, PUT'
	except:
		response = "There was an error, please try again", 400

	return response


##get all recipes
@app.route('/recipe',methods=['GET'])
def get_recipes():
	all_recipes = Recipe.query.all()
	random.shuffle(all_recipes)
	print(type(all_recipes))

	##generate aws image link
	for recipe in all_recipes:
		if recipe.image:
			recipe.image = s3.generate_presigned_url('get_object', Params = {'Bucket': S3_BUCKET, 'Key': recipe.image}, ExpiresIn = 100)

	result = recipes_schema.dump(all_recipes)
	return jsonify(result)

##get single recipe
@app.route('/recipe/<id>',methods=['GET'])
def get_recipe(id):
	recipe = Recipe.query.get(id)

	##generates aws image link
	if recipe.image:
		recipe.image = s3.generate_presigned_url('get_object', Params = {'Bucket': S3_BUCKET, 'Key': recipe.image}, ExpiresIn = 100)

	return recipe_schema.jsonify(recipe)


## run server
if __name__ == '__main__':
	app.run(debug=True)
