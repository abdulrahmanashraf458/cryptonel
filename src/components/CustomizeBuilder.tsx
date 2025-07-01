import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Star, Copy, CheckCircle2 } from "lucide-react";

interface CustomizeBuilderProps {
  isPreviewMode?: boolean;
  onCodeChange?: (code: string) => void;
}

const CustomizeBuilder: React.FC<CustomizeBuilderProps> = ({
  isPreviewMode = false,
  onCodeChange,
}) => {
  const [widgets, setWidgets] = useState<string[]>(() => {
    const saved = localStorage.getItem("custom_widgets");
    return saved ? JSON.parse(saved) : defaultWidgets;
  });

  const [widgetSettings, setWidgetSettings] = useState<
    Record<string, WidgetSettings>
  >(() => {
    const saved = localStorage.getItem("custom_widget_settings");
    return saved ? JSON.parse(saved) : defaultWidgetSettings;
  });

  const [widgetPositions, setWidgetPositions] = useState<
    Record<string, WidgetPosition>
  >({});
  const [selected, setSelected] = useState<string | null>(null);
  const [dragged, setDragged] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [resizing, setResizing] = useState<string | null>(null);
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0 });

  const GRID_SIZE = 24;
  const CELL_SIZE = 40;

  // تحديث الكود عند أي تغيير
  useEffect(() => {
    const code = encodePage(widgets, widgetSettings, widgetPositions);
    onCodeChange?.(code);
  }, [widgets, widgetSettings, widgetPositions]);

  // حفظ التغييرات في localStorage
  useEffect(() => {
    localStorage.setItem("custom_widgets", JSON.stringify(widgets));
    localStorage.setItem(
      "custom_widget_settings",
      JSON.stringify(widgetSettings)
    );
  }, [widgets, widgetSettings]);

  const handleDragStart = (id: string, e: React.DragEvent) => {
    setDragged(id);
    const rect = e.currentTarget.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handleDrag = (id: string, e: React.DragEvent) => {
    if (!dragged || !e.clientX || !e.clientY) return;

    const container = e.currentTarget.closest(".grid-container");
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left - dragOffset.x) / CELL_SIZE);
    const y = Math.floor((e.clientY - rect.top - dragOffset.y) / CELL_SIZE);

    const boundedX = Math.max(0, Math.min(x, GRID_SIZE - 1));
    const boundedY = Math.max(0, Math.min(y, GRID_SIZE - 1));

    setWidgetPositions((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        x: boundedX,
        y: boundedY,
      },
    }));
  };

  const handleDragEnd = () => {
    setDragged(null);
    setDragOffset({ x: 0, y: 0 });
  };

  const handleResizeStart = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setResizing(id);
    setResizeStart({ x: e.clientX, y: e.clientY });
  };

  const handleResize = (id: string, e: React.MouseEvent) => {
    if (!resizing) return;

    const deltaX = e.clientX - resizeStart.x;
    const deltaY = e.clientY - resizeStart.y;

    setWidgetPositions((prev) => {
      const current = prev[id] || { x: 0, y: 0, width: 200, height: 100 };
      const newWidth = Math.max(100, current.width + deltaX);
      const newHeight = Math.max(50, current.height + deltaY);

      return {
        ...prev,
        [id]: {
          ...current,
          width: newWidth,
          height: newHeight,
        },
      };
    });

    setResizeStart({ x: e.clientX, y: e.clientY });
  };

  const handleResizeEnd = () => {
    setResizing(null);
  };

  return (
    <div className="flex gap-6 min-h-[70vh]">
      {/* Sidebar */}
      <div className="w-64 bg-[#23232a] rounded-2xl p-4 flex flex-col gap-4 shadow-lg">
        <h3 className="text-lg font-bold text-white mb-2">Widgets</h3>
        {widgetList.map((widget) => (
          <div
            key={widget.id}
            draggable
            onDragStart={(e) => handleDragStart(widget.id, e)}
            onDrag={(e) => handleDrag(widget.id, e)}
            onDragEnd={handleDragEnd}
            className={`p-3 rounded-lg cursor-grab bg-[#2b2b2b] text-white border border-transparent hover:border-[#9D8DFF] transition ${
              dragged === widget.id ? "opacity-50" : ""
            }`}
          >
            {widget.name}
          </div>
        ))}
      </div>

      {/* Grid Container */}
      <div
        className={`flex-1 bg-[#18181c] rounded-2xl p-8 min-h-[70vh] shadow-lg relative ${
          isPreviewMode ? "preview-mode" : ""
        }`}
      >
        <div
          className="grid-container relative w-full h-[800px] rounded-xl"
          style={{
            backgroundImage: isPreviewMode
              ? "none"
              : `linear-gradient(#3a3a3a 1px, transparent 1px),
                 linear-gradient(90deg, #3a3a3a 1px, transparent 1px)`,
            backgroundSize: `${CELL_SIZE}px ${CELL_SIZE}px`,
          }}
        >
          {widgets.map((id) => {
            const settings = widgetSettings[id];
            const position = widgetPositions[id] || {
              x: 0,
              y: 0,
              width: 200,
              height: 100,
            };

            if (!settings?.visible) return null;

            return (
              <div
                key={id}
                draggable
                onDragStart={(e) => handleDragStart(id, e)}
                onDrag={(e) => handleDrag(id, e)}
                onDragEnd={handleDragEnd}
                className={`absolute bg-[#2b2b2b] rounded-xl p-4 cursor-move transition-all ${
                  selected === id ? "ring-2 ring-[#9D8DFF]" : ""
                } ${dragged === id ? "scale-105 shadow-lg" : ""}`}
                style={{
                  left: `${position.x * CELL_SIZE}px`,
                  top: `${position.y * CELL_SIZE}px`,
                  width: `${position.width}px`,
                  height: `${position.height}px`,
                  ...settings.style,
                }}
                onClick={() => setSelected(id)}
              >
                {renderWidget(id)}
                {!isPreviewMode && (
                  <>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemove(id);
                      }}
                      className="absolute top-1 right-1 text-[#9D8DFF] hover:text-red-500"
                      title="Remove"
                    >
                      ×
                    </button>
                    <div
                      className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
                      onMouseDown={(e) => handleResizeStart(id, e)}
                      onMouseMove={(e) => handleResize(id, e)}
                      onMouseUp={handleResizeEnd}
                      onMouseLeave={handleResizeEnd}
                    >
                      <div className="w-2 h-2 border-b-2 border-r-2 border-[#9D8DFF] absolute bottom-1 right-1" />
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Widget Settings Panel */}
      {selected && !isPreviewMode && (
        <div className="fixed top-24 right-8 w-80 bg-[#23232a] rounded-2xl p-6 shadow-2xl border border-[#9D8DFF] z-50">
          <h4 className="text-lg font-bold text-white mb-4">Widget Settings</h4>
          {/* ... إعدادات الودجت ... */}
        </div>
      )}
    </div>
  );
};

export default CustomizeBuilder;
