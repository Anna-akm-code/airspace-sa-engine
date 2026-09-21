"""Folium presentation of saved results; never fetches data or runs detection."""

from html import escape

import folium
from branca.element import Element

from .report import format_altitude_ft, format_limit, format_position_source

COLORS = dict(prohibited='red', restricted='orange', danger='purple')


def latlon(item):
    """Folium Marker/PolyLine order, unlike GeoJSON coordinates."""
    return [item['lat'], item['lon']]


def popup(text):
    # Escape provider text; keep it out of executable HTML/JavaScript.
    safe = escape(text).replace('`', '&#96;').replace('$', '&#36;')
    return folium.Popup('<pre>' + safe + '</pre>', max_width=520)


def render_map(report, *, tiles='OpenStreetMap'):
    view = folium.Map(location=[64,26], zoom_start=5, tiles=tiles)
    groups = {name: folium.FeatureGroup(name=name).add_to(view) for name in
              ('prohibited','restricted','danger','normal traffic','alerted traffic','tracks')}
    label = report['label']
    banner = escape(label + ' | ' + report['limitations'])
    view.get_root().html.add_child(Element(
        '<div style="position:fixed;top:0;left:5%;width:90%;z-index:9999;'
        'background:white;padding:8px;border:2px solid #333;font-size:12px">' + banner + '</div>'))
    for zone in report['zones']:
        color = COLORS[zone['zone_type']]
        feature = dict(type='Feature', geometry=zone['geometry'], properties={})
        # GeoJSON remains [lon,lat], including holes and MultiPolygon structure.
        layer = folium.GeoJson(feature,
            style_function=lambda feature, color=color: dict(color=color, fillColor=color, fillOpacity=0.15))
        popup(f"{label}\n{zone['name']} / {zone['id']}\n{zone['zone_type']}\n"
              f"{format_limit(zone['lower'])} -> {format_limit(zone['upper'])}\n"
              f"activation: {zone['activation_status']}").add_to(layer)
        layer.add_to(groups[zone['zone_type']])
    alerts_by_aircraft = {}
    for alert in report['alerts']:
        alerts_by_aircraft.setdefault(alert['aircraft']['icao24'], []).append(alert)
    for item in report['aircraft']:
        if item['lat'] is None or item['lon'] is None:
            continue
        alerts = alerts_by_aircraft.get(item['icao24'], [])
        status = '; '.join(f"{a['alert_type']} / {a['verification_status'].upper()} / {a['data_quality']}"
                           for a in alerts) or 'No modeled alert in this run'
        color = 'red' if alerts else ('gray' if item['freshness'] != 'fresh' else 'blue')
        text = (f"{label}\n{item['callsign'] or '-'} / {item['icao24']}\n{status}\n"
                f"freshness: {item['freshness']}; age: {item['position_age_s']} s; ground: {item['on_ground']}\n"
                f"baro: {item['baro_altitude_ft']} ft; geometric altitude: {format_altitude_ft(item['geo_altitude_ft'])}\n"
                f"source: {format_position_source(item['position_source'])}; category: {item['category']}")
        folium.Marker(latlon(item), popup=popup(text),
                      icon=folium.Icon(color=color, icon='exclamation-sign' if alerts else 'info-sign')).add_to(
                          groups['alerted traffic' if alerts else 'normal traffic'])
    for icao, rows in report['tracks'].items():
        points = [latlon(row) for row in rows if row['lat'] is not None and row['lon'] is not None]
        if len(points) > 1:
            folium.PolyLine(points, color='navy', weight=3,
                popup=popup(f'{label}\n{icao}: recorded observations; connecting lines are not a verified flight path')).add_to(groups['tracks'])
    folium.LayerControl().add_to(view)
    if report['zones'] or any(item['lat'] is not None and item['lon'] is not None for item in report['aircraft']):
        view.fit_bounds(view.get_bounds(), max_zoom=12, padding=(30,30))
    return view
