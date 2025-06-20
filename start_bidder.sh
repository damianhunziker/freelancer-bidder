#!/bin/bash

# Robuster Bidder-Starter für macOS
# Verhindert Prozess-Beendigung bei gesperrtem Mac

echo "🔒 Robuster Bidder-Starter für macOS"
echo "===================================="

# Prüfe ob bidder.py existiert
if [ ! -f "bidder.py" ]; then
    echo "❌ bidder.py nicht gefunden!"
    echo "Bitte führe das Script im Projektverzeichnis aus."
    exit 1
fi

# Prüfe ob Python verfügbar ist
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nicht gefunden!"
    exit 1
fi

# Cleanup-Funktion für graceful shutdown
cleanup() {
    echo ""
    echo "🧹 Beende Prozesse..."
    
    # Beende caffeinate
    if [ ! -z "$CAFFEINATE_PID" ]; then
        kill $CAFFEINATE_PID 2>/dev/null
        echo "✅ Sleep-Prevention deaktiviert"
    fi
    
    # Beende Python-Prozess
    if [ ! -z "$PYTHON_PID" ]; then
        kill -TERM $PYTHON_PID 2>/dev/null
        sleep 5
        kill -KILL $PYTHON_PID 2>/dev/null
        echo "✅ Bidder-Prozess beendet"
    fi
    
    echo "✅ Cleanup abgeschlossen"
    exit 0
}

# Signal Handler für graceful shutdown
trap cleanup SIGINT SIGTERM

# Starte Sleep-Prevention mit caffeinate
echo "☕ Aktiviere Sleep-Prevention..."
caffeinate -d -i -m -s &
CAFFEINATE_PID=$!
echo "✅ Sleep-Prevention aktiviert (PID: $CAFFEINATE_PID)"

# Wähle Starter-Methode
if [ -f "start_bidder_robust.py" ]; then
    echo "🚀 Starte mit robustem Python-Manager..."
    python3 start_bidder_robust.py &
    PYTHON_PID=$!
else
    echo "🚀 Starte Bidder direkt..."
    python3 bidder.py &
    PYTHON_PID=$!
fi

echo "✅ Bidder gestartet (PID: $PYTHON_PID)"
echo ""
echo "📊 Status:"
echo "   - Sleep-Prevention: Aktiv (PID: $CAFFEINATE_PID)"
echo "   - Bidder-Prozess: Aktiv (PID: $PYTHON_PID)"
echo ""
echo "💡 Tipps:"
echo "   - Drücke Ctrl+C für graceful shutdown"
echo "   - Status prüfen: ps aux | grep python"
echo "   - Logs prüfen: tail -f *.log"
echo ""

# Überwachungsloop
while true; do
    # Prüfe ob Python-Prozess noch läuft
    if ! kill -0 $PYTHON_PID 2>/dev/null; then
        echo "⚠️ Bidder-Prozess beendet - Starte neu..."
        
        if [ -f "start_bidder_robust.py" ]; then
            python3 start_bidder_robust.py &
            PYTHON_PID=$!
        else
            python3 bidder.py &
            PYTHON_PID=$!
        fi
        
        echo "🔄 Bidder neu gestartet (PID: $PYTHON_PID)"
    fi
    
    # Prüfe ob caffeinate noch läuft
    if ! kill -0 $CAFFEINATE_PID 2>/dev/null; then
        echo "⚠️ Sleep-Prevention beendet - Starte neu..."
        caffeinate -d -i -m -s &
        CAFFEINATE_PID=$!
        echo "☕ Sleep-Prevention neu gestartet (PID: $CAFFEINATE_PID)"
    fi
    
    # Status alle 5 Minuten
    if [ $(($(date +%s) % 300)) -eq 0 ]; then
        echo "📊 $(date): Bidder läuft (PID: $PYTHON_PID), Sleep-Prevention aktiv (PID: $CAFFEINATE_PID)"
    fi
    
    sleep 60
done 