from flask import jsonify

@app.route('/api/locations/cities', methods=['GET'])
def get_cities():
    """Tüm şehirleri getir"""
    return jsonify(get_all_cities())

@app.route('/api/locations/districts/<city>', methods=['GET'])
def get_districts(city):
    """Belirli bir şehrin ilçelerini getir"""
    return jsonify(get_city_districts(city))

@app.route('/api/locations/neighborhoods/<city>/<district>', methods=['GET'])
def get_neighborhoods(city, district):
    """Belirli bir ilçenin mahallelerini getir"""
    return jsonify(get_district_neighborhoods(city, district)) 