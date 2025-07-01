import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Eye, EyeOff, Save, Download, Upload } from "lucide-react";
import { toast } from "react-hot-toast";

// استيراد الأنواع والواجهات
interface WidgetPosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface WidgetStyle {
  backgroundColor?: string;
  borderColor?: string;
  borderWidth?: number;
  borderRadius?: number;
  boxShadow?: string;
  fontFamily?: string;
  fontSize?: string;
  textColor?: string;
}

interface WidgetSettingsBase {
  title: string;
  color: string;
  visible: boolean;
  font?: string;
  size?: string;
  align?: string;
  style?: WidgetStyle;
}

// قواميس الترميز
const WIDGETS_DICT = {
  totalRatings: "01",
  starDistribution: "02",
  comments: "03",
  profilePicture: "04",
  featuredQuote: "05",
  verifiedBadge: "06",
};

const COLORS_DICT = {
  "#000000": "00",
  "#FFFFFF": "01",
  "#9D8DFF": "02",
  "#60A5FA": "03",
  "#4ADE80": "04",
  "#F59E42": "05",
};

const FONTS_DICT = {
  Arial: "00",
  Roboto: "01",
  Montserrat: "02",
  Tahoma: "03",
};

const SIZES_DICT = {
  small: "01",
  medium: "02",
  large: "03",
};

const ALIGN_DICT = {
  left: "00",
  center: "01",
  right: "02",
};

// دالة الترميز المحدثة
function encodeWidget(
  id: keyof typeof WIDGETS_DICT,
  settings: WidgetSettingsBase,
  pos: WidgetPosition
): string {
  return [
    WIDGETS_DICT[id],
    String(pos.x).padStart(3, "0"),
    String(pos.y).padStart(3, "0"),
    String(pos.width).padStart(3, "0"),
    String(pos.height).padStart(3, "0"),
    COLORS_DICT[settings.color as keyof typeof COLORS_DICT] || "00",
    FONTS_DICT[(settings.font as keyof typeof FONTS_DICT) || "Arial"] || "00",
    SIZES_DICT[(settings.size as keyof typeof SIZES_DICT) || "medium"] || "02",
    ALIGN_DICT[(settings.align as keyof typeof ALIGN_DICT) || "center"] || "01",
  ].join("-");
}

function encodePage(
  widgets: string[],
  widgetSettings: Record<string, WidgetSettingsBase>,
  widgetPositions: Record<string, WidgetPosition>
): string {
  return widgets
    .map((id) =>
      encodeWidget(
        id as keyof typeof WIDGETS_DICT,
        widgetSettings[id],
        widgetPositions[id] || { x: 0, y: 0, width: 200, height: 100 }
      )
    )
    .join("|");
}

const Builder: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [pageCode, setPageCode] = useState("");
  const [showCode, setShowCode] = useState(false);

  // ... باقي الكود من CustomizeBuilder ...

  return (
    <div className="min-h-screen bg-[#18181c]">
      {/* شريط الأدوات العلوي */}
      <div className="fixed top-0 left-0 right-0 h-16 bg-[#23232a] border-b border-[#3a3a3a] z-50 flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-white">Page Builder</h1>
          <span className="text-[#C4C4C7]">ID: {id}</span>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsPreviewMode(!isPreviewMode)}
            className="p-2 hover:bg-[#3a3a3a] rounded-lg transition-colors"
            title={isPreviewMode ? "Exit Preview" : "Preview Mode"}
          >
            {isPreviewMode ? (
              <EyeOff className="w-5 h-5 text-[#9D8DFF]" />
            ) : (
              <Eye className="w-5 h-5 text-[#9D8DFF]" />
            )}
          </button>

          <button
            onClick={() => setShowCode(!showCode)}
            className="p-2 hover:bg-[#3a3a3a] rounded-lg transition-colors"
            title="Show/Hide Code"
          >
            <Code className="w-5 h-5 text-[#9D8DFF]" />
          </button>

          <button
            onClick={() => {
              navigator.clipboard.writeText(pageCode);
              toast.success("Page code copied to clipboard!");
            }}
            className="p-2 hover:bg-[#3a3a3a] rounded-lg transition-colors"
            title="Copy Code"
          >
            <Copy className="w-5 h-5 text-[#9D8DFF]" />
          </button>

          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-[#9D8DFF] text-white rounded-lg hover:bg-[#8C6FE6] transition-colors"
          >
            Save & Exit
          </button>
        </div>
      </div>

      {/* منطقة البناء */}
      <div className="pt-16">
        <CustomizeBuilder
          isPreviewMode={isPreviewMode}
          onCodeChange={setPageCode}
        />
      </div>

      {/* نافذة الكود */}
      {showCode && (
        <div className="fixed bottom-0 left-0 right-0 h-64 bg-[#23232a] border-t border-[#3a3a3a] p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-white font-bold">Page Code</h3>
            <button
              onClick={() => setShowCode(false)}
              className="text-[#C4C4C7] hover:text-white"
            >
              ×
            </button>
          </div>
          <textarea
            value={pageCode}
            readOnly
            className="w-full h-40 bg-[#18181c] text-white p-3 rounded-lg font-mono text-sm"
          />
        </div>
      )}
    </div>
  );
};

export default Builder;
