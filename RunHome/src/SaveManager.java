import java.io.*;
import java.nio.file.*;

/**
 * Simple save/load using a plain key=value text file.
 */
public class SaveManager {
    private static final Path SAVE_FILE = Path.of(System.getProperty("user.home"), ".runhome_save.txt");

    public int bestScore = 0;
    public int cash      = 0;

    public SaveManager() { load(); }

    public void save() {
        try {
            String data = "best=" + bestScore + "\ncash=" + cash + "\n";
            Files.writeString(SAVE_FILE, data);
        } catch (IOException e) {
            System.err.println("Save failed: " + e.getMessage());
        }
    }

    private void load() {
        if (!Files.exists(SAVE_FILE)) return;
        try {
            for (String line : Files.readAllLines(SAVE_FILE)) {
                String[] parts = line.split("=", 2);
                if (parts.length != 2) continue;
                switch (parts[0].trim()) {
                    case "best" -> bestScore = Integer.parseInt(parts[1].trim());
                    case "cash" -> cash      = Integer.parseInt(parts[1].trim());
                }
            }
        } catch (IOException | NumberFormatException e) {
            System.err.println("Load failed: " + e.getMessage());
        }
    }
}
