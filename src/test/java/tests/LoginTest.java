package tests;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import org.junit.Assert;

import java.util.concurrent.TimeUnit;

public class LoginTest {
    public static void main(String[] args) {

        System.setProperty("webdriver.chrome.driver","chromedriver.exe");
        WebDriver driver = new ChromeDriver();

        String url = "http://176.36.27.131:8180/";

        driver.get(url);
        driver.manage().window().maximize();
        driver.manage().timeouts().pageLoadTimeout(10, TimeUnit.SECONDS);


                driver.manage().timeouts().pageLoadTimeout(10,TimeUnit.SECONDS);

        WebElement email = driver.findElement(By.id("username"));
        WebElement password = driver.findElement(By.id("password"));
        WebElement loginButton = driver.findElement(By.id("login-signin"));

        email.clear();
        System.out.println("Entering the email");
        email.sendKeys("thadmin");

        password.clear();
        System.out.println("entering the password");
        password.sendKeys("tickethub");

        System.out.println("Clicking login button");
        loginButton.click();

        String title = "Welcome - LambdaTest";

        String actualTitle = driver.getTitle();

        System.out.println("Verifying the page title has started");
        Assert.assertEquals(actualTitle,title,"Page title doesnt match");

        System.out.println("The page title has been successfully verified");

        System.out.println("User logged in successfully");

        driver.quit();
    }
}