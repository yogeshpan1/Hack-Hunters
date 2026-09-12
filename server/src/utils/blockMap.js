import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CSV_PATH = path.join(__dirname, "..", "..", "data", "class_details.csv");

let cachedBlockMap = null;

/**
 * Reads server/data/class_details.csv and returns:
 *   { [roomName]: { code, block, csvCapacity } }
 * keyed on the friendly room name (matches `Room.roomName` in MongoDB).
 */
export function loadBlockMap() {
  if (cachedBlockMap) {
    return cachedBlockMap;
  }

  const raw = fs.readFileSync(CSV_PATH, "utf-8");
  const lines = raw.split(/\r?\n/).filter((line) => line.trim().length > 0);

  const blockMap = {};

  // Skip the header row.
  for (const line of lines.slice(1)) {
    const [roomName, code, block, capacity] = line.split(",");

    blockMap[roomName.trim()] = {
      code: code.trim(),
      block: block.trim(),
      csvCapacity: parseInt(capacity.trim(), 10),
    };
  }

  cachedBlockMap = blockMap;

  return blockMap;
}

/**
 * Reads server/data/class_details.csv and returns an ordered array of
 * { roomName, roomCode, block, capacity } - one per CSV row, in file order.
 * Used by the seed script to create real Room documents.
 */
export function loadRoomList() {
  const blockMap = loadBlockMap();

  return Object.entries(blockMap).map(([roomName, info]) => ({
    roomName,
    roomCode: info.code,
    block: info.block,
    capacity: info.csvCapacity,
  }));
}
