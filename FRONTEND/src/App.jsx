import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Navigation, 
  Battery, 
  Signal, 
  ShieldAlert, 
  ArrowUp, 
  ArrowDown, 
  Power,
  Terminal as LogIcon,
  Video,
  Eye,
  Crosshair,
  Map as MapIcon,
  Target
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import logo from './assets/logo_new.png';
import feniks_blue from './assets/feniks_blue.png';
import feniks_red from './assets/feniks_red.png';

// Fix for default marker icons in Leaflet
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

let globalWs = null;

// --- Sub-Components ---

const Card = ({ title, icon: Icon, children, className }) => (
  <div className={cn("relative group bg-black/60 backdrop-blur-md border rounded-xl p-4 overflow-hidden transition-all duration-500", className)}>
    <div className="flex items-center gap-2 mb-4 border-b border-white/5 pb-2">
      <Icon className="w-4 h-4 opacity-70" />
      <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-80">{title}</h3>
    </div>
    {children}
  </div>
);

const TelemetryItem = ({ label, value, unit, colorClass = "text-cyan-400" }) => (
  <div className="flex flex-col">
    <span className="text-[9px] uppercase text-gray-500 font-bold tracking-tighter">{label}</span>
    <div className="flex items-baseline gap-1">
      <span className={cn("text-xl font-mono font-black tracking-tighter", colorClass)}>{value}</span>
      <span className="text-[9px] text-gray-400 font-bold">{unit}</span>
    </div>
  </div>
);

function ChangeView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] !== 0 && center[1] !== 0) {
      map.setView(center, zoom || map.getZoom());
    }
  }, [center, map]);
  return null;
}

// --- Main Dashboard ---

export default function App() {
  const [drones, setDrones] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [activeDroneIdx, setActiveDroneIdx] = useState(0); 
  const [mapType, setMapType] = useState('SATELLITE'); // 'SATELLITE' veya 'STREET'
  // Varsayılan konum (Kocaeli Üniversitesi Havacılık ve Uzay Bilimleri Fakültesi)
  const [userLocation] = useState([40.712633, 30.026206]); 
  const logEndRef = useRef(null);

  const isAttackMode = activeDroneIdx === 1;
  const themeColorClass = isAttackMode ? "text-red-500" : "text-cyan-500";
  const themeBorderClass = isAttackMode ? "border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.05)]" : "border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.05)]";

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    let reconnectTimeout;
    const connect = () => {
      if (globalWs && (globalWs.readyState === WebSocket.OPEN || globalWs.readyState === WebSocket.CONNECTING)) return;
      globalWs = new WebSocket('ws://localhost:8000/ws/telemetry');
      globalWs.onopen = () => setIsConnected(true);
      globalWs.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'telemetry') {
          if (message.data.drones) setDrones(message.data.drones);
          if (message.data.logs) {
            message.data.logs.forEach(log => {
              const time = new Date().toLocaleTimeString([], { hour12: false });
              setLogs(prev => [...prev, { time, msg: log.msg, type: log.type }]);
            });
          }
        }
      };
      globalWs.onclose = () => {
        setIsConnected(false);
        globalWs = null;
        reconnectTimeout = setTimeout(connect, 3000);
      };
    };
    connect();
    return () => clearTimeout(reconnectTimeout);
  }, []);

  const sendCommand = async (cmd, drone_id = null) => {
    const time = new Date().toLocaleTimeString([], { hour12: false });
    const targetId = drone_id || (activeDroneIdx + 1);
    const targetDesc = drone_id ? `Birim ${drone_id}` : "TÜM BİRİMLER";
    setLogs(prev => [...prev, { time, msg: `${targetDesc}: ${cmd.toUpperCase()} komutu iletildi`, type: "warning" }]);
    try {
      const url = drone_id ? `http://localhost:8000/command/${cmd}?drone_id=${targetId}` : `http://localhost:8000/command/${cmd}`;
      await fetch(url, { method: 'POST' });
    } catch (err) {
      setLogs(prev => [...prev, { time, msg: "İletişim Hatası", type: "error" }]);
    }
  };

  const displayDrones = drones.length > 0 ? drones : [
    { id: 1, alt: 0, lat: 0, lon: 0, heading: 0, battery: 100, armed: false, mode: "DISCONNECTED" },
    { id: 2, alt: 0, lat: 0, lon: 0, heading: 0, battery: 100, armed: false, mode: "DISCONNECTED" }
  ];

  const activeDrone = displayDrones[activeDroneIdx] || displayDrones[0];

  return (
    <div className={cn("min-h-screen bg-[#05070a] text-white p-6 font-sans transition-all duration-700", 
      isAttackMode ? "bg-[radial-gradient(circle_at_center,_rgba(239,68,68,0.08)_0%,_black_100%)]" : "bg-[radial-gradient(circle_at_center,_rgba(6,182,212,0.08)_0%,_black_100%)]")}>
      
      <header className={cn("flex justify-between items-center mb-6 border-b pb-4 transition-colors", isAttackMode ? "border-red-500/20" : "border-cyan-500/20")}>
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-3 border-r border-white/10 pr-5">
            <img src={isAttackMode ? feniks_red : feniks_blue} alt="Feniks" className="h-10 w-auto object-contain" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tighter italic uppercase">AEROKOU <span className={themeColorClass}>{isAttackMode ? "SALDIRI EKRANI" : "GÖZLEMCİ EKRANI"}</span></h1>
            <p className="text-[10px] font-bold opacity-40 tracking-[0.3em]">SİSTEM DURUMU: {isConnected ? "ÇEVRİMİÇİ" : "ÇEVRİMDIŞI"}</p>
          </div>
        </div>
        
        <div className="flex bg-white/5 rounded-xl p-1 border border-white/5 backdrop-blur-md">
          <button onClick={() => setActiveDroneIdx(0)} className={cn("px-6 py-2.5 rounded-lg font-black text-[10px] tracking-widest transition-all flex items-center gap-2", activeDroneIdx === 0 ? "bg-cyan-500 text-black shadow-[0_0_20px_rgba(6,182,212,0.4)]" : "text-cyan-500/40 hover:text-cyan-400")}>
            <Eye className="w-3.5 h-3.5" /> GÖZLEMCİ DRONE
          </button>
          <button onClick={() => setActiveDroneIdx(1)} className={cn("px-6 py-2.5 rounded-lg font-black text-[10px] tracking-widest transition-all flex items-center gap-2", activeDroneIdx === 1 ? "bg-red-500 text-black shadow-[0_0_20px_rgba(239,68,68,0.4)]" : "text-red-500/40 hover:text-red-400")}>
            <Crosshair className="w-3.5 h-3.5" /> SALDIRI DRONE'U
          </button>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-160px)]">
        
        <div className="col-span-3 flex flex-col gap-4 overflow-hidden">
          <Card title="Uçuş Parametreleri" icon={Activity} className={themeBorderClass}>
            <div className="grid grid-cols-2 gap-y-6 gap-x-2">
              <TelemetryItem label="İrtifa" value={activeDrone.alt.toFixed(1)} unit="m" colorClass={themeColorClass} />
              <TelemetryItem label="Hız" value="0.0" unit="m/s" colorClass={themeColorClass} />
              <TelemetryItem label="Enlem" value={activeDrone.lat.toFixed(5)} unit="°" colorClass={themeColorClass} />
              <TelemetryItem label="Boylam" value={activeDrone.lon.toFixed(5)} unit="°" colorClass={themeColorClass} />
              <TelemetryItem label="Açı" value={activeDrone.heading.toFixed(0)} unit="°" colorClass={themeColorClass} />
              <TelemetryItem label="Batarya" value={activeDrone.battery} unit="%" colorClass="text-emerald-500" />
            </div>
          </Card>

          <div className={cn("flex-grow border rounded-xl overflow-hidden relative min-h-[300px]", themeBorderClass)}>
            <MapContainer 
              center={userLocation} 
              zoom={16} 
              style={{ height: '100%', width: '100%' }} 
              zoomControl={false}
            >
              {mapType === 'SATELLITE' ? (
                <TileLayer 
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" 
                  attribution="Esri World Imagery"
                  maxZoom={19}
                />
              ) : (
                <TileLayer 
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" 
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  maxZoom={19}
                />
              )}
              
              <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2">
                <button 
                  onClick={() => setMapType('SATELLITE')}
                  className={cn(
                    "p-2 rounded-lg border transition-all flex items-center justify-center gap-2 text-[9px] font-black tracking-widest uppercase backdrop-blur-md",
                    mapType === 'SATELLITE' 
                      ? (isAttackMode ? "bg-red-500 border-red-400 text-black shadow-[0_0_10px_rgba(239,68,68,0.4)]" : "bg-cyan-500 border-cyan-400 text-black shadow-[0_0_10px_rgba(6,182,212,0.4)]")
                      : "bg-black/60 border-white/10 text-white/70 hover:bg-black/80"
                  )}
                >
                  <Video className="w-3 h-3" /> UYDU
                </button>
                <button 
                  onClick={() => setMapType('STREET')}
                  className={cn(
                    "p-2 rounded-lg border transition-all flex items-center justify-center gap-2 text-[9px] font-black tracking-widest uppercase backdrop-blur-md",
                    mapType === 'STREET' 
                      ? (isAttackMode ? "bg-red-500 border-red-400 text-black shadow-[0_0_10px_rgba(239,68,68,0.4)]" : "bg-cyan-500 border-cyan-400 text-black shadow-[0_0_10px_rgba(6,182,212,0.4)]")
                      : "bg-black/60 border-white/10 text-white/70 hover:bg-black/80"
                  )}
                >
                  <MapIcon className="w-3 h-3" /> SOKAK
                </button>
              </div>

              <ChangeView 
                center={activeDrone.lat !== 0 ? [activeDrone.lat, activeDrone.lon] : userLocation} 
                zoom={16}
              />
              {displayDrones.map(d => d.lat !== 0 && (
                <Marker key={d.id} position={[d.lat, d.lon]} icon={new L.DivIcon({
                  html: `<div style="transform: rotate(${d.heading}deg); transition: all 0.5s;">
                          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="${d.id === 1 ? '#06b6d4' : '#ef4444'}" stroke-width="2.5" style="filter: drop-shadow(0 0 8px ${d.id === activeDrone.id ? (d.id === 1 ? '#06b6d4' : '#ef4444') : 'transparent'})">
                            ${d.id === 1 
                              ? '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>' // Eye Icon
                              : '<circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/>' // Crosshair Icon
                            }
                          </svg>
                          <span style="position:absolute; top:-14px; left:50%; transform:translateX(-50%); color:white; font-size:9px; font-weight:black; background:${d.id === 1 ? '#06b6d4' : '#ef4444'}; padding:0 4px; border-radius:3px; white-space:nowrap">${d.id === 1 ? 'GÖZLEMCİ' : 'SALDIRI'}</span>
                        </div>`,
                  className: '', iconSize: [36, 36], iconAnchor: [18, 18]
                })} />
              ))}
            </MapContainer>
            <div className="absolute top-2 left-2 bg-black/80 text-[8px] font-black p-1 rounded border border-white/10 z-[1000] uppercase tracking-widest">Harita Takibi Aktif</div>
          </div>
        </div>

        <div className="col-span-6 flex flex-col gap-4">
          <div className={cn("h-2/3 bg-black border rounded-2xl relative overflow-hidden group transition-all duration-700", themeBorderClass)}>
            {isAttackMode && (
              <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center">
                <div className="w-64 h-64 border border-red-500/20 rounded-full animate-pulse flex items-center justify-center">
                  <div className="w-48 h-48 border border-red-500/40 rounded-full flex items-center justify-center">
                    <div className="w-1 h-1 bg-red-500" />
                    <div className="absolute w-full h-[1px] bg-red-500/30" />
                    <div className="absolute h-full w-[1px] bg-red-500/30" />
                  </div>
                </div>
                <div className="absolute top-10 left-10 w-12 h-12 border-t-4 border-l-4 border-red-500/50" />
                <div className="absolute top-10 right-10 w-12 h-12 border-t-4 border-r-4 border-red-500/50" />
                <div className="absolute bottom-10 left-10 w-12 h-12 border-b-4 border-l-4 border-red-500/50" />
                <div className="absolute bottom-10 right-10 w-12 h-12 border-b-4 border-r-4 border-red-500/50" />
              </div>
            )}
            
            <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.02),rgba(0,255,0,0.01),rgba(0,0,255,0.02))] z-10 bg-[length:100%_4px,4px_100%]" />
            <div className="absolute inset-0 flex items-center justify-center bg-[#080a0c]">
              <div className="text-center flex flex-col items-center">
                <img src={logo} alt="Aerokou" className="w-64 h-auto opacity-10 mb-6" />
                <div className="opacity-20 flex flex-col items-center">
                  <Video className={cn("w-12 h-12 mb-4 animate-pulse", isAttackMode ? "text-red-500" : "text-cyan-500")} />
                  <p className="font-mono text-[10px] tracking-[0.5em] uppercase font-black">Video Akışı Bekleniyor</p>
                </div>
              </div>
            </div>
          </div>

          <Card title="Sistem Kayıtları" icon={LogIcon} className={cn("flex-grow", themeBorderClass)}>
            <div className="font-mono text-[10px] h-full overflow-y-auto space-y-2 scrollbar-hide pr-2">
              {logs.map((log, i) => (
                <div key={i} className="flex gap-4 border-l-2 border-white/5 pl-3 py-0.5">
                  <span className="text-white/20 shrink-0 font-bold tracking-tighter">{log.time}</span>
                  <span className={cn("tracking-tight font-medium", {
                    "text-cyan-400": log.type === "info" && !isAttackMode,
                    "text-red-400": log.type === "info" && isAttackMode,
                    "text-orange-400": log.type === "warning",
                    "text-red-600 font-black": log.type === "error",
                    "text-emerald-400": log.type === "success",
                  })}>{log.msg}</span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </Card>
        </div>

        <div className="col-span-3 flex flex-col gap-4">
          <Card title="Operasyonel Güç" icon={Power} className={themeBorderClass}>
            <div className="grid gap-3">
              <button onClick={() => sendCommand('arm', activeDroneIdx + 1)} className={cn("w-full py-4 font-black rounded-xl transition-all flex items-center justify-center gap-3 text-xs tracking-widest", isAttackMode ? "bg-red-500/20 border-2 border-red-500 text-red-500 hover:bg-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.2)]" : "bg-cyan-500/20 border-2 border-cyan-500 text-cyan-500 hover:bg-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.2)]")}>
                <ShieldAlert className="w-5 h-5" /> SİSTEMİ ARM ET
              </button>
              <button onClick={() => sendCommand('disarm', activeDroneIdx + 1)} className="w-full py-3 bg-zinc-900 border border-white/5 text-gray-500 font-bold rounded-xl hover:bg-zinc-800 transition-all text-[9px] tracking-[0.2em]">GÜVENLİ DISARM</button>
            </div>
          </Card>

          <Card title="Uçuş Modu Seçimi" icon={Activity} className={themeBorderClass}>
            <div className="grid grid-cols-2 gap-2">
              {['GUIDED', 'AUTO', 'RTL', 'LAND'].map(mode => (
                <button key={mode} onClick={() => sendCommand('mode', activeDroneIdx + 1)} className={cn("py-3 text-[10px] font-black rounded-lg border transition-all tracking-widest", activeDrone.mode === mode ? (isAttackMode ? "bg-red-500 border-red-400 text-black shadow-[0_0_25px_rgba(239,68,68,0.6)] scale-[1.02] brightness-125" : "bg-cyan-500 border-cyan-400 text-black shadow-[0_0_25px_rgba(6,182,212,0.6)] scale-[1.02] brightness-125") : "bg-white/5 border-white/5 text-white/40 hover:bg-white/10")}>{mode}</button>
              ))}
            </div>
          </Card>

          <Card title="Görev İcra" icon={ArrowUp} className={themeBorderClass}>
            <div className="grid gap-3">
              <button onClick={() => sendCommand('start-mission')} className={cn("w-full py-5 text-black font-black rounded-2xl transition-all flex items-center justify-center gap-3 text-sm tracking-tighter shadow-lg hover:scale-[1.01] active:scale-95", isAttackMode ? "bg-red-600 shadow-red-900/40 hover:shadow-red-500/50 hover:bg-red-500" : "bg-cyan-600 shadow-cyan-900/40 hover:shadow-cyan-500/50 hover:bg-cyan-500")}>
                <ArrowUp className="w-5 h-5" /> GÖREVİ BAŞLAT (TÜM BİRİMLER)
              </button>
              <button onClick={() => sendCommand('failsafe-mission')} className={cn("w-full py-4 border", isAttackMode ? "text-cyan-500 bg-cyan-950/40 hover:bg-cyan-900/40 border-cyan-900/30 hover:shadow-[0_0_15px_rgba(6,182,212,0.2)]" : "text-red-500 bg-red-950/40 hover:bg-red-900/40 border-red-900/30 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]" , "font-black rounded-xl transition-all text-[10px] tracking-widest uppercase hover:scale-[1.01] active:scale-95")}>Acil Durum / Failsafe</button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
