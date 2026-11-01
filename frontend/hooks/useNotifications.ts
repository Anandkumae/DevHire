"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { NotificationItem } from "@/types";
import { api } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

export function useNotifications() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    try {
      const items = await api.getNotifications();
      setNotifications(items);
      setUnreadCount(items.filter((n) => !n.is_read).length);
    } catch (e) {
      console.error("Failed to load notifications:", e);
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();

    if (!user) return;

    // Connect to WebSocket
    const wsUrl = `ws://localhost:8000/api/v1/notifications/ws/${user.id}`;
    let ws: WebSocket;

    try {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const newNotif: NotificationItem = {
            id: payload.id || Math.random().toString(),
            user_id: user.id,
            type: payload.type || "system",
            title: payload.title || "New Notification",
            message: payload.message || "",
            data: payload.data || null,
            is_read: false,
            created_at: payload.timestamp || new Date().toISOString(),
          };

          setNotifications((prev) => [newNotif, ...prev]);
          setUnreadCount((c) => c + 1);
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      ws.onerror = () => {
        // Fallback gracefully without breaking UI
      };
    } catch (e) {
      console.warn("WebSocket connection skipped or unavailable:", e);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [user, fetchNotifications]);

  const markRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error(err);
    }
  };

  const markAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error(err);
    }
  };

  return {
    notifications,
    unreadCount,
    markRead,
    markAllRead,
    refresh: fetchNotifications,
  };
}

