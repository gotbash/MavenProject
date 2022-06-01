package tests;
import org.junit.Test;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.firefox.FirefoxDriver;
public class OpenBrowserFF {
    @Test
    public void Openrowser() {
        System.setProperty("webdriver.gecko.driver", "geckodriver.exe");
        WebDriver driver = new FirefoxDriver();
        driver.get("http://176.36.27.131:8180/#/");
        driver.quit();
    }
}

