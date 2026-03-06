import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { useTranslation } from '../context/LanguageContext'

// Fix for default Leaflet marker icons in React
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const restaurants = [
    { id: 1, name: "Bombay Brasserie", lat: 18.5204, lng: 73.8567, rating: "4.8" },
    { id: 2, name: "The Curry Collective", lat: 18.5300, lng: 73.8400, rating: "4.5" },
    { id: 3, name: "Tandoor Royale", lat: 18.5400, lng: 73.8600, rating: "4.7" },
    { id: 4, name: "Spice Republic", lat: 18.5150, lng: 73.8700, rating: "4.6" },
    { id: 5, name: "Zest Dining", lat: 18.5100, lng: 73.8500, rating: "4.9" },
]

export default function MapSection() {
    const navigate = useNavigate()
    const { t } = useTranslation()

    // Assuming Pune center
    const center = [18.5204, 73.8567]

    return (
        <section className="lp-map-section" style={{ padding: '80px 48px', borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
            <div style={{ maxWidth: '1200px', margin: '0 auto', textAlign: 'center', marginBottom: '40px' }}>
                <h2 style={{ fontSize: '36px', fontWeight: '900', color: '#fff', marginBottom: '16px' }}>{t('cta_heading')}</h2>
                <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.45)' }}>Discover Sizzle-powered restaurants near you.</p>
            </div>

            <div style={{ height: '500px', width: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                <MapContainer center={center} zoom={13} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    />
                    {restaurants.map(rest => (
                        <Marker key={rest.id} position={[rest.lat, rest.lng]}>
                            <Popup className="lp-map-popup">
                                <div style={{ padding: '4px', textAlign: 'center' }}>
                                    <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 'bold' }}>{rest.name}</h4>
                                    <p style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#666' }}>Rating: {rest.rating} ★</p>
                                    <button
                                        onClick={(e) => {
                                            e.preventDefault()
                                            navigate('/login')
                                        }}
                                        style={{
                                            background: 'var(--accent)',
                                            color: '#fff',
                                            border: 'none',
                                            padding: '6px 16px',
                                            borderRadius: '4px',
                                            cursor: 'pointer',
                                            fontSize: '12px',
                                            fontWeight: 'bold'
                                        }}
                                    >
                                        Visit
                                    </button>
                                </div>
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>
            </div>
        </section>
    )
}
