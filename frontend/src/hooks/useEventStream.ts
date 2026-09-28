import { useEffect, useRef, useState } from "react";
import type { SocEvent, SimulatorStatus, Alert, WsMessage } from "@/types/event";
import type { Incident } from "@/types/incident";

interface UseEventStreamResult {
  connected: boolean;
  liveEvents: SocEvent[];
  liveAlerts: Alert[];
  liveIncidents: Incident[];
  status: SimulatorStatus | null;
}

const MAX_BUFFERED_EVENTS = 200;
const MAX_BUFFERED_ALERTS = 100;
const MAX_BUFFERED_INCIDENTS = 50;

export function useEventStream(): UseEventStreamResult {
  const [connected, setConnected] = useState(false);
  const [liveEvents, setLiveEvents] = useState<SocEvent[]>([]);
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);
  const [liveIncidents, setLiveIncidents] = useState<Incident[]>([]);
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const retryRef = useRef<number>(0);

  useEffect(() => {
    let ws: WebSocket;
    let closedByEffect = false;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${protocol}://${window.location.host}/ws/events`);

      ws.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
      };

      ws.onmessage = (event) => {
        const msg: WsMessage = JSON.parse(event.data);
        if (msg.type === "event") {
          setLiveEvents((prev) => [msg.data, ...prev].slice(0, MAX_BUFFERED_EVENTS));
        } else if (msg.type === "alert") {
          setLiveAlerts((prev) => [msg.data, ...prev].slice(0, MAX_BUFFERED_ALERTS));
        } else if (msg.type === "incident") {
          // an incident is re-sent every time another alert joins it; latest wins
          setLiveIncidents((prev) =>
            [msg.data, ...prev.filter((i) => i.incident_id !== msg.data.incident_id)].slice(
              0,
              MAX_BUFFERED_INCIDENTS
            )
          );
        } else if (msg.type === "status") {
          setStatus(msg.data);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!closedByEffect) {
          const delay = Math.min(1000 * 2 ** retryRef.current, 10000);
          retryRef.current += 1;
          retryTimeout = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      closedByEffect = true;
      clearTimeout(retryTimeout);
      ws?.close();
    };
  }, []);

  return { connected, liveEvents, liveAlerts, liveIncidents, status };
}
