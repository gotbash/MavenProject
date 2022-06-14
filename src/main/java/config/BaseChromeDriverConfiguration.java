package config;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.annotations.AfterSuite;
import org.testng.annotations.BeforeSuite;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

public class BaseChromeDriverConfiguration {
    public static WebDriver driver;

    @BeforeSuite
    public void initializeWebDriver() throws IOException {
        System.setProperty("webdriver.chrome.driver", "\\src\\drivers\\chromedriver.exe");
        driver = new ChromeDriver();

        driver.manage().window().maximize();

        // Implicit wait
        driver.manage().timeouts().implicitlyWait(10, TimeUnit.SECONDS);

        // To open Gmail site
        driver.get("https:// www.gmail.com");
    }

    @AfterSuite
    public void quitDriver() {
        driver.quit();
    }
}