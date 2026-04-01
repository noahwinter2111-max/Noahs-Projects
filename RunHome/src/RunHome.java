import javax.swing.*;

public class RunHome extends JFrame {
    public static final int W = 1024;
    public static final int H = 768;

    public RunHome() {
        GamePanel panel = new GamePanel();
        setTitle("RUN HOME — Outrun the Law");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setResizable(false);
        add(panel);
        pack();
        setLocationRelativeTo(null);
        setVisible(true);
        panel.start();
    }
}
