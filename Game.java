import javax.swing.*;

public class Game {
    public static void main(String[] args) {
        JFrame f = new JFrame();
        JButton b = new JButton("0");
        b.setFont(b.getFont().deriveFont(64f));
        b.addActionListener(e -> b.setText(String.valueOf(Integer.parseInt(b.getText()) + 1)));
        f.add(b);
        f.setSize(300, 200);
        f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        f.setVisible(true);
    }
}
