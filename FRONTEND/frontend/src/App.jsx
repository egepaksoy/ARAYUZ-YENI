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
  Map as MapIcon
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

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

// Custom Drone Icon
const droneIcon = new L.DivIcon({
  html: `<div style="transform: rotate(0deg);"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="m12 8 4 4-4 4-4-4z"/><path d="M12 2v4"/><path d="M12 18v4"/><path d="M2 12h4"/><path d="M18 12h4"/></svg></div>`,
  className: 'custom-drone-icon',
  iconSize: [32, 32],
  iconAnchor: [16, 16]
});

// Component to auto-center map
function ChangeView({ center }) {
  const map = useMap();
  if (center[0] !== 0 && center[1] !== 0) {
    map.setView(center, map.getZoom());
  }
  return null;
}
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Helper for Tailwind class merging
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// --- Sub-Components ---

const Card = ({ title, icon: Icon, children, className }) => (
  <div className={cn("relative group bg-black/40 backdrop-blur-md border border-cyan-500/20 rounded-xl p-4 overflow-hidden", className)}>
    <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500/40 group-hover:bg-cyan-400 transition-colors" />
    <div className="flex items-center gap-2 mb-4 border-b border-cyan-500/10 pb-2">
      <Icon className="w-4 h-4 text-cyan-400" />
      <h3 className="text-xs font-bold uppercase tracking-widest text-cyan-100/70">{title}</h3>
    </div>
    {children}
  </div>
);

const TelemetryItem = ({ label, value, unit, color = "cyan" }) => (
  <div className="flex flex-col">
    <span className="text-[10px] uppercase text-gray-500 font-semibold">{label}</span>
    <div className="flex items-baseline gap-1">
      <span className={cn("text-2xl font-mono font-bold tracking-tighter", {
        "text-cyan-400": color === "cyan",
        "text-orange-400": color === "orange",
        "text-emerald-400": color === "green",
      })}>{value}</span>
      <span className="text-[10px] text-gray-400">{unit}</span>
    </div>
  </div>
);

// --- Main Dashboard ---

export default function App() {
  const [telemetry, setTelemetry] = useState({
    alt: 0.0,
    lat: 0.0,
    lon: 0.0,
    heading: 0,
    battery: 100,
    armed: false,
    status: "STANDBY",
    mode: "UNKNOWN",
    connected: false
  });
  
  const [logs, setLogs] = useState([]);
  const logEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Telemetry Polling
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8000/telemetry');
        const data = await response.json();
        setTelemetry(data);
        
        // Handle backend logs if present
        if (data.logs && data.logs.length > 0) {
          data.logs.forEach(log => {
            addLog(log.msg, log.type);
          });
        }
      } catch (err) {
        setTelemetry(prev => ({ ...prev, connected: false }));
      }
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  const addLog = (msg, type = "info") => {
    const time = new Date().toLocaleTimeString([], { hour12: false });
    setLogs(prev => [...prev, { time, msg, type }]);
  };

  const sendCommand = async (cmd) => {
    addLog(`Executing: ${cmd.toUpperCase()}...`, "warning");
    try {
      const response = await fetch(`http://localhost:8000/command/${cmd}`, { method: 'POST' });
      if (response.ok) {
        addLog(`System: ${cmd} success`, "success");
      }
    } catch (err) {
      addLog(`Error: ${cmd} failed`, "error");
    }
  };

  return (
    <div className="min-h-screen bg-[#05070a] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-900/10 via-black to-black text-white p-6 font-sans selection:bg-cyan-500/30">
      
      {/* Backend Connection Overlay */}
      {!telemetry.connected && (
        <div className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center">
          <div className="text-center p-8 border border-cyan-500/30 rounded-2xl bg-black/50 shadow-[0_0_50px_rgba(6,182,212,0.2)]">
            <div className="w-16 h-16 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin mx-auto mb-6"></div>
            <h2 className="text-2xl font-black tracking-tighter uppercase italic text-cyan-500 mb-2">
              Bağlantı Bekleniyor
            </h2>
            <p className="text-gray-400 font-mono text-sm uppercase tracking-widest">
              Backend sunucusu ile iletişim kuruluyor...
            </p>
          </div>
        </div>
      )}

      {/* HUD Header */}
      <header className="flex justify-between items-center mb-6 border-b border-cyan-500/20 pb-4">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 bg-cyan-500 rounded-lg flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.5)]">
            <Navigation className="text-black" />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tighter uppercase italic">Aerokou <span className="text-cyan-500 font-light">GCS_v1.0</span></h1>
            <div className="flex gap-4 text-[10px] text-cyan-400/60 uppercase font-bold tracking-widest">
              <span className="flex items-center gap-1"><Signal className="w-3 h-3" /> Link Status</span>
              {/* Batarya kontrolu calisiyorsa dursun */}
              <span className="flex items-center gap-1"><Battery className="w-3 h-3" /> {telemetry.battery}%</span>
            </div>
          </div>
        </div>
        
        <div className="flex gap-2">
          <div className="px-4 py-2 rounded border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 font-mono text-sm flex items-center gap-2">
            <Activity className="w-4 h-4" />
            MODE: {telemetry.mode || "N/A"}
          </div>
          <div className={cn("px-4 py-2 rounded border font-mono text-sm flex items-center gap-2", 
            telemetry.armed ? "bg-red-500/10 border-red-500 text-red-500" : "bg-cyan-500/10 border-cyan-500 text-cyan-500")}>
            <Activity className={cn("w-4 h-4", telemetry.armed && "animate-pulse")} />
            {telemetry.armed ? "ARMED / HOT" : "DISARMED / SAFE"}
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-160px)]">
        
        {/* Left: Telemetry Stats */}
        <div className="col-span-3 flex flex-col gap-4">
          <Card title="Vertical Flight Data" icon={ArrowUp}>
            <div className="grid gap-6">
              <TelemetryItem label="Altitude" value={(telemetry.alt || 0).toFixed(1)} unit="m" color="cyan" />
              <TelemetryItem label="Vertical Speed" value="0.0" unit="m/s" />
              <TelemetryItem label="Heading" value={telemetry.heading || 0} unit="°" />
            </div>
          </Card>

          <Card title="GPS Coordinates" icon={Navigation}>
            <div className="grid gap-4">
              <TelemetryItem label="Latitude" value={(telemetry.lat || 0).toFixed(6)} unit="deg" color="orange" />
              <TelemetryItem label="Longitude" value={(telemetry.lon || 0).toFixed(6)} unit="deg" color="orange" />
            </div>
          </Card>
        </div>

        {/* Center: Video & Map */}
        <div className="col-span-6 flex flex-col gap-4">
          <div className="flex-grow grid grid-rows-2 gap-4 h-full">
            {/* Video Stream */}
            <div className="bg-black border border-cyan-500/30 rounded-xl relative group overflow-hidden shadow-2xl">
              {/* Scanline effect overlay */}
              <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.02),rgba(0,255,0,0.01),rgba(0,0,255,0.02))] z-10 bg-[length:100%_2px,3px_100%]" />
              
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/50">
                <div className="text-center">
                  <Video className="w-12 h-12 text-cyan-500/20 mx-auto mb-2 animate-pulse" />
                  <p className="text-cyan-500/40 font-mono text-sm tracking-widest uppercase">Awaiting Video Feed...</p>
                </div>
              </div>
              
              {/* UI Overlay on Video */}
              <div className="absolute top-4 right-4 flex gap-2 z-20">
                <span className="bg-red-600 text-[10px] font-bold px-2 py-0.5 rounded animate-pulse">REC</span>
                <span className="bg-black/60 text-[10px] font-bold px-2 py-0.5 rounded border border-white/10">00:12:44</span>
              </div>
            </div>

            {/* Map */}
            <div className="bg-black border border-cyan-500/30 rounded-xl relative overflow-hidden shadow-2xl">
              <MapContainer 
                center={[telemetry.lat || 0, telemetry.lon || 0]} 
                zoom={15} 
                style={{ height: '100%', width: '100%' }}
                zoomControl={false}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <ChangeView center={[telemetry.lat || 0, telemetry.lon || 0]} />
                {telemetry.lat !== 0 && (
                  <Marker 
                    position={[telemetry.lat, telemetry.lon]} 
                    icon={new L.DivIcon({
                      html: `<div style="transform: rotate(${telemetry.heading || 0}deg); transition: transform 0.5s ease-in-out;">
                              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 0 8px rgba(6,182,212,0.8))">
                                <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                                <path d="m12 8 4 4-4 4-4-4z"/>
                                <path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>
                              </svg>
                            </div>`,
                      className: 'custom-drone-icon',
                      iconSize: [40, 40],
                      iconAnchor: [20, 20]
                    })}
                  />
                )}
              </MapContainer>
              
              {/* Map Overlay Labels */}
              <div className="absolute top-2 left-2 z-[1000] flex gap-2">
                <span className="bg-black/80 backdrop-blur-md border border-cyan-500/30 text-[10px] font-bold px-2 py-1 rounded text-cyan-400 flex items-center gap-1">
                  <MapIcon className="w-3 h-3" /> LIVE TRACKING
                </span>
              </div>
            </div>
          </div>

          <Card title="Mission Logs" icon={LogIcon} className="h-48">
            <div className="font-mono text-[11px] overflow-y-auto h-full space-y-1 scrollbar-hide">
              {logs.map((log, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-gray-600">[{log.time}]</span>
                  <span className={cn({
                    "text-cyan-400": log.type === "info",
                    "text-orange-400": log.type === "warning",
                    "text-red-400": log.type === "error",
                    "text-emerald-400": log.type === "success",
                  })}>{log.msg}</span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </Card>
        </div>

        {/* Right: Controls */}
        <div className="col-span-3 flex flex-col gap-4">
          <Card title="Primary Controls" icon={Power}>
            <div className="grid gap-3">
              <button 
                onClick={() => sendCommand('arm')}
                className="w-full py-3 bg-red-500/10 border border-red-500/40 text-red-400 font-bold rounded-lg hover:bg-red-500/20 transition-all flex items-center justify-center gap-2"
              >
                <ShieldAlert className="w-4 h-4" /> ARM SYSTEM
              </button>
              <button 
                onClick={() => sendCommand('disarm')}
                className="w-full py-3 bg-zinc-800 border border-white/10 text-white font-bold rounded-lg hover:bg-zinc-700 transition-all"
              >
                DISARM
              </button>
            </div>
          </Card>

          <Card title="Flight Actions" icon={ArrowUp}>
            <div className="grid gap-3">
              <button 
                onClick={() => sendCommand('start-mission')}
                className="w-full py-4 bg-cyan-500 text-black font-black rounded-lg hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2"
              >
                <ArrowUp className="w-5 h-5" /> START-MISSION
              </button>
              <button 
                onClick={() => sendCommand('failsafe-mission')}
                className="w-full py-4 bg-red-500 text-black font-black rounded-lg hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2"
              >
                <ArrowDown className="w-5 h-5" /> FAILSAFE
              </button>
            </div>
          </Card>
        
        </div>
      </div>
    </div>
  );
}
