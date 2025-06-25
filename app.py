from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import logging
import base64
from PIL import Image
import io
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps

import zipfile
import io
import os
from flask import send_file
from datetime import datetime
import tempfile
import shutil



# Initialize Flask app
app = Flask(__name__)

# Configuration
class Config:
    # Database configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'singora_db')
    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', '12345')
    API_KEY = os.getenv('API_KEY', '12345')

app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database Models
class ImageData(db.Model):
    __tablename__ = 'singora_images'
    
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.LargeBinary(length=16777215), nullable=False)  # MEDIUMBLOB in MySQL
    label_name = db.Column(db.String(255), nullable=False, index=True)
    date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self, include_image=False):
        result = {
            'id': self.id,
            'label_name': self.label_name,
            'date': self.date.isoformat() if self.date else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
        
        # Only include image data if specifically requested (for performance)
        if include_image:
            result['image'] = base64.b64encode(self.image).decode('utf-8') if self.image else None
            
        return result

# Utility functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_image_data(file_data):
    """Validate that the data is a valid image"""
    try:
        image = Image.open(io.BytesIO(file_data))
        image.verify()  # Verify it's a valid image
        return True
    except Exception as e:
        logger.warning(f"Invalid image data: {e}")
        return False

# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('singora-API-Key')
        if not api_key or api_key != app.config['API_KEY']:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Error handlers
@app.errorhandler(413)
def file_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected'
        }), 503

@app.route('/api/v1/images', methods=['POST'])
@require_api_key
def upload_image():
    """Upload image with label"""
    try:
        # Validate request
        if 'image' not in request.files and 'image_data' not in request.form:
            return jsonify({'error': 'No image provided'}), 400
        
        if 'label_name' not in request.form:
            return jsonify({'error': 'Label name is required'}), 400
        
        label_name = request.form['label_name'].strip()
        if not label_name:
            return jsonify({'error': 'Label name cannot be empty'}), 400
        
        # Handle file upload (multipart/form-data)
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'File type not allowed'}), 400
            
            file_data = file.read()
        
        # Handle base64 image data
        elif 'image_data' in request.form:
            try:
                image_data = request.form['image_data']
                # Remove data URL prefix if present
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',', 1)[1]
                
                file_data = base64.b64decode(image_data)
                    
            except Exception as e:
                logger.error(f"Base64 decode error: {e}")
                return jsonify({'error': 'Invalid base64 image data'}), 400
        
        # Validate file size
        if len(file_data) > app.config['MAX_CONTENT_LENGTH']:
            return jsonify({'error': 'File too large'}), 413
        
        # Validate image data
        if not validate_image_data(file_data):
            return jsonify({'error': 'Invalid image data'}), 400
        
        # Create database record with auto timestamp and date
        image_record = ImageData(
            image=file_data,  # Store binary data directly
            label_name=label_name
            # date and timestamp will be auto-generated
        )
        
        db.session.add(image_record)
        db.session.commit()
        
        logger.info(f"Image uploaded successfully with ID: {image_record.id}")
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'data': image_record.to_dict()  # Don't include image data in response
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error occurred', "details":str(e)}), 500
    
  
    
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': 'Upload failed', "details": str(e)}), 500




@app.route('/api/v1/images/download/all', methods=['GET'])
@require_api_key
def download_all_images():
    """Download all images organized by label_name in separate ZIP files within a main ZIP"""
    try:
        # Create a temporary directory to store individual label ZIP files
        temp_dir = tempfile.mkdtemp()
        main_zip_path = os.path.join(temp_dir, 'all_images_by_labels.zip')
        
        # Get all unique label names
        labels = db.session.query(ImageData.label_name).distinct().all()
        
        if not labels:
            return jsonify({'error': 'No images found'}), 404
        
        with zipfile.ZipFile(main_zip_path, 'w', zipfile.ZIP_DEFLATED) as main_zip:
            for (label_name,) in labels:
                # Get all images for this label
                images = ImageData.query.filter(ImageData.label_name == label_name).all()
                
                if images:
                    # Create ZIP content for this label in memory
                    label_zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(label_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as label_zip:
                        for image in images:
                            if image.image:
                                # Create filename with timestamp for uniqueness
                                timestamp_str = image.timestamp.strftime('%Y%m%d_%H%M%S')
                                filename = f"{timestamp_str}_{image.id}.jpg"
                                
                                # Add image to label ZIP
                                label_zip.writestr(filename, image.image)
                    
                    # Add the label ZIP to main ZIP
                    label_zip_buffer.seek(0)
                    main_zip.writestr(f"{label_name}.zip", label_zip_buffer.read())
                    label_zip_buffer.close()
        
        # Send the main ZIP file
        return send_file(
            main_zip_path,
            as_attachment=True,
            download_name=f"all_images_by_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mimetype='application/zip'
        )
        
    except Exception as e:
        logger.error(f"Download all images error: {e}")
        # Clean up temp directory if it exists
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': 'Failed to create download'}), 500



@app.route('/api/v1/images/download/label/<label_name>', methods=['GET'])
@require_api_key
def download_images_by_label(label_name):
    """Download all images for a specific label as a ZIP file"""
    try:
        # Build query
        query = ImageData.query.filter(ImageData.label_name == label_name)
        
        # Get all images for the label
        images = query.order_by(ImageData.timestamp.desc()).all()
        
        if not images:
            return jsonify({'error': f'No images found for label: {label_name}'}), 404
        
        # Create temporary file for ZIP
        temp_fd, temp_path = tempfile.mkstemp(suffix='.zip')
        
        try:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for image in images:
                    if image.image and len(image.image) > 0:
                        # Create filename with timestamp and date for better organization
                        timestamp_str = image.timestamp.strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp_str}_{image.id}.jpg"
                        
                        # Add image to ZIP
                        zip_file.writestr(filename, image.image)
            
            # Generate download filename
            download_filename = f"{label_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            # Return file and schedule cleanup
            def remove_file(response):
                try:
                    os.close(temp_fd)
                    os.unlink(temp_path)
                except Exception:
                    pass
                return response
            
            response = send_file(
                temp_path,
                as_attachment=True,
                download_name=download_filename,
                mimetype='application/zip'
            )
            
            # Clean up temp file after response
            response.call_on_close(lambda: remove_file(response))
            return response
            
        except Exception as e:
            # Clean up temp file on error
            try:
                os.close(temp_fd)
                os.unlink(temp_path)
            except Exception:
                pass
            raise e
        
    except Exception as e:
        logger.error(f"Download images by label error: {e}")
        return jsonify({'error': 'Failed to create download'}), 500

@app.route('/api/v1/images/download/date/<date>', methods=['GET'])
@require_api_key
def download_images_by_date(date):
    """Download all images for a specific date, organized by label folders within ZIP"""
    try:
        # Validate date format
        try:
            filter_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Optional label filtering
        label_name = request.args.get('label_name')
        
        # Build query
        query = ImageData.query.filter(ImageData.date == filter_date)
        
        if label_name:
            query = query.filter(ImageData.label_name == label_name)
        
        # Get all images for the date
        images = query.order_by(ImageData.label_name, ImageData.timestamp).all()
        
        if not images:
            return jsonify({'error': f'No images found for date: {date}'}), 404
        
        # Create temporary file for ZIP
        temp_fd, temp_path = tempfile.mkstemp(suffix='.zip')
        
        try:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for image in images:
                    if image.image and len(image.image) > 0:
                        # Create folder structure: label_name/filename
                        timestamp_str = image.timestamp.strftime('%H%M%S')  # Just time for same date
                        filename = f"{image.label_name}/{timestamp_str}_{image.id}.jpg"
                        
                        # Add image to ZIP with folder structure
                        zip_file.writestr(filename, image.image)
            
            # Generate download filename
            label_suffix = f"_{label_name}" if label_name else ""
            download_filename = f"images_{date}{label_suffix}_{datetime.now().strftime('%H%M%S')}.zip"
            
            def remove_file(response):
                try:
                    os.close(temp_fd)
                    os.unlink(temp_path)
                except Exception:
                    pass
                return response
            
            response = send_file(
                temp_path,
                as_attachment=True,
                download_name=download_filename,
                mimetype='application/zip'
            )
            
            response.call_on_close(lambda: remove_file(response))
            return response
            
        except Exception as e:
            try:
                os.close(temp_fd)
                os.unlink(temp_path)
            except Exception:
                pass
            raise e
            
    except Exception as e:
        logger.error(f"Download images by date error: {e}")
        return jsonify({'error': 'Failed to create download'}), 500

@app.route('/api/v1/images/download/label/<label_name>/date/<date>', methods=['GET'])
@require_api_key
def download_images_by_label_and_date(label_name, date):
    """Download images filtered by both label_name and specific date"""
    try:
        # Validate date format
        try:
            filter_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Query parameters for additional filtering
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 1000, type=int), 1000)
        download_format = request.args.get('format', 'zip').lower()
        
        # Build query with both label and date filters
        query = ImageData.query.filter(
            ImageData.label_name == label_name,
            ImageData.date == filter_date
        )
        
        # Get images (with pagination support for very large datasets)
        if download_format == 'json':
            # For JSON response, use pagination
            paginated_images = query.order_by(ImageData.timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            images = paginated_images.items
            
            if not images:
                return jsonify({
                    'message': f'No images found for label "{label_name}" on date {date}',
                    'data': [],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 0,
                        'has_next': False,
                        'has_prev': False
                    },
                    'filters': {
                        'label_name': label_name,
                        'date': date
                    }
                }), 200
            
            # Return JSON response with image data
            return jsonify({
                'data': [image.to_dict(include_image=True) for image in images],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated_images.total,
                    'pages': paginated_images.pages,
                    'has_next': paginated_images.has_next,
                    'has_prev': paginated_images.has_prev
                },
                'filters': {
                    'label_name': label_name,
                    'date': date
                },
                'download_url': f'/api/v1/images/download/label/{label_name}/date/{date}?format=zip'
            }), 200
        
        else:  # ZIP download
            # Get all images for ZIP download
            images = query.order_by(ImageData.timestamp.desc()).all()
            
            if not images:
                return jsonify({
                    'error': f'No images found for label "{label_name}" on date {date}'
                }), 404
            
            # Create temporary file for ZIP
            temp_fd, temp_path = tempfile.mkstemp(suffix='.zip')
            
            try:
                with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for image in images:
                        if image.image and len(image.image) > 0:
                            # Create filename with time (since date is already specified)
                            time_str = image.timestamp.strftime('%H%M%S')
                            filename = f"{time_str}_{image.id}.jpg"
                            
                            # Add image to ZIP
                            zip_file.writestr(filename, image.image)
                
                # Generate download filename
                download_filename = f"{label_name}_{date}_{datetime.now().strftime('%H%M%S')}.zip"
                
                def remove_file(response):
                    try:
                        os.close(temp_fd)
                        os.unlink(temp_path)
                    except Exception:
                        pass
                    return response
                
                response = send_file(
                    temp_path,
                    as_attachment=True,
                    download_name=download_filename,
                    mimetype='application/zip'
                )
                
                response.call_on_close(lambda: remove_file(response))
                return response
                
            except Exception as e:
                try:
                    os.close(temp_fd)
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise e
        
    except Exception as e:
        logger.error(f"Download images by label and date error: {e}")
        return jsonify({'error': 'Failed to retrieve/download images'}), 500

@app.route('/api/v1/images/download/label/<label_name>/date-range', methods=['GET'])
@require_api_key
def download_images_by_label_and_date_range(label_name):
    """Download images filtered by label_name and date range"""
    try:
        # Required query parameters
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        if not date_from or not date_to:
            return jsonify({
                'error': 'Both date_from and date_to parameters are required',
                'example': f'/api/v1/images/download/label/{label_name}/date-range?date_from=2024-01-01&date_to=2024-01-31'
            }), 400
        
        # Validate date formats
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        if from_date > to_date:
            return jsonify({'error': 'date_from cannot be later than date_to'}), 400
        
        # Optional parameters
        download_format = request.args.get('format', 'zip').lower()
        organize_by_date = request.args.get('organize_by_date', 'true').lower() == 'true'
        
        # Build query
        query = ImageData.query.filter(
            ImageData.label_name == label_name,
            ImageData.date >= from_date,
            ImageData.date <= to_date
        )
        
        # Get images
        images = query.order_by(ImageData.date, ImageData.timestamp).all()
        
        if not images:
            return jsonify({
                'error': f'No images found for label "{label_name}" between {date_from} and {date_to}'
            }), 404
        
        if download_format == 'json':
            # Group by date for JSON response
            images_by_date = {}
            for image in images:
                date_key = image.date.isoformat()
                if date_key not in images_by_date:
                    images_by_date[date_key] = []
                images_by_date[date_key].append(image.to_dict(include_image=True))
            
            return jsonify({
                'label_name': label_name,
                'date_range': {
                    'from': date_from,
                    'to': date_to
                },
                'total_images': len(images),
                'dates_with_images': len(images_by_date),
                'data': images_by_date,
                'download_url': f'/api/v1/images/download/label/{label_name}/date-range?date_from={date_from}&date_to={date_to}&format=zip'
            }), 200
        
        else:  # ZIP download
            # Create temporary file for ZIP
            temp_fd, temp_path = tempfile.mkstemp(suffix='.zip')
            
            try:
                with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for image in images:
                        if image.image and len(image.image) > 0:
                            if organize_by_date:
                                # Organize in date folders: 2024-01-15/143022_123.jpg
                                date_folder = image.date.isoformat()
                                time_str = image.timestamp.strftime('%H%M%S')
                                filename = f"{date_folder}/{time_str}_{image.id}.jpg"
                            else:
                                # Flat structure with date in filename: 20240115_143022_123.jpg
                                datetime_str = image.timestamp.strftime('%Y%m%d_%H%M%S')
                                filename = f"{datetime_str}_{image.id}.jpg"
                            
                            zip_file.writestr(filename, image.image)
                
                # Generate download filename
                download_filename = f"{label_name}_{date_from}_to_{date_to}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                
                def remove_file(response):
                    try:
                        os.close(temp_fd)
                        os.unlink(temp_path)
                    except Exception:
                        pass
                    return response
                
                response = send_file(
                    temp_path,
                    as_attachment=True,
                    download_name=download_filename,
                    mimetype='application/zip'
                )
                
                response.call_on_close(lambda: remove_file(response))
                return response
                
            except Exception as e:
                try:
                    os.close(temp_fd)
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise e
        
    except Exception as e:
        logger.error(f"Download images by label and date range error: {e}")
        return jsonify({'error': 'Failed to retrieve/download images'}), 500


@app.route('/api/v1/images/download/info', methods=['GET'])
@require_api_key
def get_download_info():
    """Get information about available downloads (labels and counts)"""
    try:
        # Get label statistics
        label_stats = db.session.query(
            ImageData.label_name,
            db.func.count(ImageData.id).label('count'),
            db.func.min(ImageData.date).label('earliest_date'),
            db.func.max(ImageData.date).label('latest_date')
        ).group_by(ImageData.label_name).all()
        
        # Get total statistics
        total_images = ImageData.query.count()
        total_labels = len(label_stats)
        
        return jsonify({
            'total_images': total_images,
            'total_labels': total_labels,
            'labels': [
                {
                    'label_name': stat.label_name,
                    'image_count': stat.count,
                    'earliest_date': stat.earliest_date.isoformat() if stat.earliest_date else None,
                    'latest_date': stat.latest_date.isoformat() if stat.latest_date else None
                }
                for stat in label_stats
            ],
            'download_endpoints': {
                'all_labels': '/api/v1/images/download/all',
                'by_label': '/api/v1/images/download/label/<label_name>',
                'by_date': '/api/v1/images/download/date/<date>',
                'by_label_and_date': '/api/v1/images/download/label/<label_name>/date/<date>',
                'by_label_and_date_range': '/api/v1/images/download/label/<label_name>/date-range?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD',
                'info': '/api/v1/images/download/info'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get download info error: {e}")
        return jsonify({'error': 'Failed to retrieve download information'}), 500



#     """Download image as binary data"""
#     try:
#         image = ImageData.query.get(image_id)
        
#         if not image:
#             return jsonify({'error': 'Image not found'}), 404
        
#         # Return image as binary response
#         return app.response_class(
#             image.image,
#             mimetype='image/jpeg',  # You might want to store and use actual mime type
#             headers={'Content-Disposition': f'attachment; filename=image_{image_id}.jpg'}
#         )
        
#     except Exception as e:
#         logger.error(f"Download image error: {e}")
#         return jsonify({'error': 'Failed to download image'}), 500

@app.route('/api/v1/images/<int:image_id>', methods=['DELETE'])
@require_api_key
def delete_image(image_id):
    """Delete image by ID"""
    try:
        image = ImageData.query.get(image_id)
        
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        # Delete from database
        db.session.delete(image)
        db.session.commit()
        
        logger.info(f"Image deleted successfully: {image_id}")
        
        return jsonify({'message': 'Image deleted successfully'}), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during deletion: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    
    except Exception as e:
        logger.error(f"Delete image error: {e}")
        return jsonify({'error': 'Failed to delete image'}), 500

@app.route('/api/v1/labels', methods=['GET'])
@require_api_key
def get_labels():
    """Get all unique labels with counts"""
    try:
        labels = db.session.query(
            ImageData.label_name,
            db.func.count(ImageData.id).label('count')
        ).group_by(ImageData.label_name).all()
        
        return jsonify({
            'data': [{'label_name': label[0], 'count': label[1]} for label in labels]
        }), 200
        
    except Exception as e:
        logger.error(f"Get labels error: {e}")
        return jsonify({'error': 'Failed to retrieve labels'}), 500

@app.route('/api/v1/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Get database statistics"""
    try:
        total_images = ImageData.query.count()
        total_labels = db.session.query(ImageData.label_name).distinct().count()
        
        # Get images by date
        images_by_date = db.session.query(
            ImageData.date,
            db.func.count(ImageData.id).label('count')
        ).group_by(ImageData.date).order_by(ImageData.date.desc()).limit(30).all()
        
        return jsonify({
            'total_images': total_images,
            'total_labels': total_labels,
            'images_by_date': [
                {'date': date.isoformat(), 'count': count} 
                for date, count in images_by_date
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500

# Database initialization
def create_tables():
    """Create database tables"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

if __name__ == '__main__':
    # Create tables if they don't exist
    create_tables()
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )